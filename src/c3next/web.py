from pkg_resources import resource_filename
from binascii import unhexlify
from datetime import datetime
import json
from pytz import UTC

from twisted.application import service
from twisted.internet import reactor, endpoints, defer
from twisted.python import log
from twisted.web.server import Site
from twisted.web.static import File

import sqlalchemy as sa

from klein import Klein

import jinja2

import c3next.db as db
from c3next.config import DEFAULT_PER_PAGE
from c3next.models import Beacon, Listener, BytesEncoder
from c3next.util import ceildiv


@defer.inlineCallbacks
def del_obj(table, o_id, cache=None):
    if cache and o_id in cache:
        del cache[o_id]
    cur = yield db.execute(table.delete().where(table.c.id == o_id))
    yield cur.close()


def ago(last_seen):
    td = datetime.now(tz=UTC) - last_seen
    if td.seconds < 2:
        return "Now"
    elif td.seconds < 60:
        return "{} seconds ago".format(td.seconds)
    elif td.seconds / 60 < 60:
        return "{} minutes ago".format(td.seconds/60)
    elif td.seconds / 3600 < 24:
        return "{} hours ago".format(td.seconds/3600)
    else:
        return "{} days ago".format(td.days)


app = Klein()
env = jinja2.Environment(
    loader=jinja2.PackageLoader(__name__, 'templates'))
env.filters['ago'] = ago


@app.route('/static/', branch=True)
def static(request):
    return File(resource_filename(__name__, 'static/'))


@app.route('/')
def index(request):
    page = env.get_template('index.html')
    return page.render()


def query_filter(request, query, search_fields=[]):
    """ Uses requestHeaders to add filtering methods to query"""
    def _last(header, cls=None):
        if header not in request.args:
            return None
        header = request.args[header][-1]
        return cls(header)

    def _all(header, cls=None):
        if header not in request.args:
            return []
        if cls is not None:
            return [cls(h) for h in request.args[header]]
        return request.args[header]

    pagination = {}
    limit = _last('limit', cls=int)
    if limit:
        pagination['per_page'] = limit
    else:
        pagination['per_page'] = DEFAULT_PER_PAGE
    query = query.limit(pagination['per_page'])

    page = _last('p', cls=int)
    if page:
        pagination['cur_page'] = page
        offset = (page - 1) * pagination['per_page']
    else:
        offset = _last('offset', cls=int)
        if offset:
            pagination['cur_page'] = ceildiv(offset, pagination['per_page'])
    if offset:
        query = query.offset(offset)
    if 'cur_page' not in pagination:
        pagination['cur_page'] = 1

    search = _all('search')
    or_payload = []
    for h in search:
        for sf in search_fields:
            if isinstance(sf.type, sa.sql.sqltypes.String):
                or_payload.append(
                    sa.func.lower(sf).like("%"+sa.func.lower(h)+"%"))
            else:
                or_payload.append(
                    sf.like("%"+h+"%"))
    query = query.where(sa.or_(*or_payload))
    print(or_payload)
    log.msg("Filter Query: {}".format(query))
    search = ' '.join([s for s in search])
    return query, pagination, search


def model_rp(rp, cls):
    return [cls(row=r) for r in rp]


@defer.inlineCallbacks
def get_count(table, column=None, conn=None):
    column = table.c.id if column is None else column
    query = sa.func.count(column)
    if conn is None:
        rp = yield db.execute(query)
        count = yield rp.scalar()
        rp.close()
    else:
        rp = yield conn.execute(query)
        count = yield rp.scalar()
    defer.returnValue(count)


@app.route('/beacons')
@defer.inlineCallbacks
def b_list(request):
    page = env.get_template('beacon_list.html')
    conn = yield db.get_connection()

    # Todo replace pagination dict with attrs obj
    query, pagination, search = query_filter(request, db.beacons.select(),
                                             search_fields=[db.beacons.c.name])
    cur = yield conn.execute(query)
    if not search:
        pagination['num_objects'] = yield get_count(db.beacons, conn=conn)
    else:
        pagination['num_objects'] = cur.rowcount
    pagination['num_pages'] = ceildiv(pagination['num_objects'],
                                      pagination['per_page'])
    results = yield cur.fetchall()
    beacons = model_rp(results, Beacon)
    if request.requestHeaders.hasHeader('Accept'):
        accept = request.requestHeaders.getRawHeaders('Accept')[0]
        if accept.endswith('json'):
            request.responseHeaders.addRawHeader('Content-Type', accept)
            defer.returnValue(
                json.dumps([b.flatten() for b in beacons],
                           cls=BytesEncoder))
    query = db.listeners.select().where(db.listeners.c.id.in_(
        [b['listener_id'] for b in beacons if b['listener_id']]))
    cur = yield conn.execute(query)
    results = yield cur.fetchall()
    listeners = {i['id']: i for i in model_rp(results, Listener)}
    yield conn.close()
    defer.returnValue(page.render(obj_list=beacons,
                                  relation=listeners,
                                  pagination=pagination,
                                  search=search))


@app.route('/listeners')
@defer.inlineCallbacks
def l_list(request):
    page = env.get_template('listener_list.html')
    query, pagination, search = query_filter(
        request, db.listeners.select(),
        search_fields=[db.listeners.c.name, db.listeners.c.id])
    conn = yield db.get_connection()
    cur = yield conn.execute(query)
    if not search:
        pagination['num_objects'] = yield get_count(db.listeners, conn=conn)
    else:
        pagination['num_objects'] = cur.rowcount
    pagination['num_pages'] = ceildiv(pagination['num_objects'],
                                      pagination['per_page'])
    results = yield cur.fetchall()
    listeners = model_rp(results, Listener)
    yield conn.close()
    if request.requestHeaders.hasHeader('Accept'):
        accept = request.requestHeaders.getRawHeaders('Accept')[0]
        if accept.endswith('json'):
            request.responseHeaders.addRawHeader('Content-Type', accept)
            defer.returnValue(
                json.dumps([l.flatten() for l in listeners],
                           cls=BytesEncoder))
    defer.returnValue(page.render(obj_list=listeners,
                                  pagination=pagination,
                                  search=search))


def last_header(headers, header, cls=None):
    if not headers.hasHeader("limit"):
        return None
    header = headers.getRawHeaders('limit')[-1]
    return cls(header)


@app.route('/beacons/<string:b_id>', methods=['GET', 'POST', 'DELETE'])
@defer.inlineCallbacks
def b_detail(request, b_id):
    b = yield Beacon.fetch(b_id)
    if not b:
        request.setResponseCode(404)
        defer.returnValue("Not Found")
    if request.method == 'POST':
        if 'name' in request.args:
            b['name'] = request.args['name'][0]
            yield b.save()
            from listenerd import BEACONS
            cache_key = unhexlify(b_id)
            if cache_key in BEACONS:
                BEACONS[cache_key]['name'] = b['name']
    elif request.method == 'DELETE':
        yield b.delete()
        request.setResponseCode(201)
        from listenerd import BEACONS
        del BEACONS[b_id]
        defer.returnValue(None)
    else:
        if request.requestHeaders.hasHeader('Accept'):
            accept = request.requestHeaders.getRawHeaders('Accept')[0]
            if accept.endswith('json'):
                request.responseHeaders.addRawHeader('Content-Type', accept)
                defer.returnValue(b.flatten())
    page = env.get_template('beacon_detail.html')
    defer.returnValue(page.render(obj=b))


@app.route('/listeners/<string:l_id>', methods=['GET', 'POST', 'DELETE'])
@defer.inlineCallbacks
def l_detail(request, l_id):
    page = env.get_template('listener_detail.html')
    l = yield Listener.fetch(l_id)
    if request.method == 'POST':
        if 'name' in request.args:
            l['name'] = request.args['name'][0]
            yield l.save()
            from listenerd import LISTENERS
            LISTENERS[l_id]['name'] = l['name']
    elif request.method == 'DELETE':
        yield l.delete()
        request.setResponseCode(201)
        from listenerd import LISTENERS
        del LISTENERS[l_id]
        defer.returnValue(None)
    defer.returnValue(page.render(obj=l))


class WebService(service.Service):
    def __init__(self, endpoint_desc):
        self.endpoint_desc = endpoint_desc

    def startService(self):
        self.endpoint = endpoints.serverFromString(reactor, self.endpoint_desc)
        self.endpoint.listen(Site(app.resource()))
