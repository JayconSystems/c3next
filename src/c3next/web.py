from pkg_resources import resource_filename
from binascii import unhexlify, hexlify
from datetime import datetime
import json
from pytz import UTC

from twisted.application import service
from twisted.internet import reactor, endpoints, defer
from twisted.python import log
from twisted.web.server import Site
from twisted.web.static import File

from klein import Klein

import jinja2

import c3next.db as db
from c3next.config import DEFAULT_PER_PAGE
from c3next.models import Beacon, Listener, BytesEncoder


@defer.inlineCallbacks
def del_obj(table, hex_id, cache=None):
    o_id = unhexlify(hex_id)
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
env.filters['hexlify'] = hexlify
env.filters['ago'] = ago


@app.route('/static/', branch=True)
def static(request):
    return File(resource_filename(__name__, 'static/'))


@app.route('/')
def index(request):
    page = env.get_template('index.html')
    return page.render()


def query_filter(request, query, search_field=None):
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

    limit = _last('limit', cls=int)
    if limit:
        query = query.limit(limit)
    else:
        query = query.limit(DEFAULT_PER_PAGE)

    offset = _last('offset', cls=int)
    if offset:
        query = query.offset(offset)

    search = _all('search')
    for h in search:
        query = query.where(search_field.like("%"+h+"%"))
    log.msg("Filter Query: {}".format(query))
    return query


def model_rp(rp, cls):
    return [cls(row=r) for r in rp]


@app.route('/beacons')
@defer.inlineCallbacks
def b_list(request):
    page = env.get_template('beacon_list.html')
    query = query_filter(request, db.beacons.select(),
                         search_field=db.beacons.c.name)
    conn = yield db.get_connection()
    cur = yield conn.execute(query)
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
    defer.returnValue(page.render(obj_list=beacons, relation=listeners))


@app.route('/listeners')
@defer.inlineCallbacks
def l_list(request):
    page = env.get_template('listener_list.html')
    query = query_filter(request, db.listeners.select(),
                         search_field=db.listeners.c.name)
    conn = yield db.get_connection()
    cur = yield conn.execute(query)
    results = yield cur.fetchall()
    listeners = model_rp(results, Listener)
    yield conn.close()
    defer.returnValue(page.render(obj_list=listeners))


def last_header(headers, header, cls=None):
    if not headers.hasHeader("limit"):
        return None
    header = headers.getRawHeaders('limit')[-1]
    return cls(header)


@app.route('/beacons/<string:hex_id>', methods=['GET', 'POST', 'DELETE'])
@defer.inlineCallbacks
def b_detail(request, hex_id):
    b_id = unhexlify(hex_id)
    b = yield Beacon.fetch(b_id)
    if not b:
        request.setResponseCode(404)
        defer.returnValue("Not Found")
    if request.method == 'POST':
        if 'name' in request.args:
            b['name'] = request.args['name'][0]
            yield b.save()
            from listenerd import BEACONS
            BEACONS[b_id] = b
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


@app.route('/listeners/<string:hex_id>', methods=['GET', 'POST', 'DELETE'])
@defer.inlineCallbacks
def l_detail(request, hex_id):
    page = env.get_template('listener_detail.html')
    l_id = unhexlify(hex_id)
    l = yield Listener.fetch(l_id)
    if request.method == 'POST':
        if 'name' in request.args:
            l['name'] = request.args['name'][0]
            yield l.save()
            from listenerd import LISTENERS
            LISTENERS[l_id] = l
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
