from binascii import hexlify, unhexlify
from datetime import datetime
from functools import reduce
import operator
import json
from pytz import UTC
from calendar import timegm

from twisted.internet import defer
from twisted.python import log

import c3next.db as db
from c3next.config import (DK0_INTERVAL, DK1_INTERVAL,
                           BEACON_LISTENER_TIMEOUT)
from c3next.util import evolve_dk

from sqlalchemy.dialects.postgresql import insert


class BytesEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return timegm(obj.utctimetuple())
        if isinstance(obj, DirtyContainer):
            return obj.flatten()
        return json.JSONEncoder(self, obj)


class MissingData(KeyError):
    pass


class DirtyContainer(object):
    _private_fields = []
    _table = None
    _pk_column = None

    @classmethod
    @defer.inlineCallbacks
    def fetch(cls, pk, conn=None):
        results = yield cls.fetch_many([pk], conn)
        if results != []:
            defer.returnValue(results[0])
        else:
            defer.returnValue(None)

    @classmethod
    def hex_fetch(cls, hex_pk, conn=None):
        return cls.fetch(unhexlify(hex_pk))

    @classmethod
    @defer.inlineCallbacks
    def fetch_many(cls, id_list, conn=None):
        if id_list == []:
            defer.returnValue([])
        if cls._table is None:
            raise NotImplementedError(
                "Must specify _table in {}".format(cls.__name__))
        if cls._pk_column is None:
            pk_c = cls._table.c.id
        else:
            pk_c = cls._pk_column
        if not conn:
            _conn = yield db.get_connection()
        else:
            _conn = conn
        rp = yield _conn.execute(cls._table.select().where(
            pk_c.in_(id_list)))
        results = yield rp.fetchall()
        if not conn:
            yield _conn.close()
        if results:
            defer.returnValue([cls(r) for r in results])
        else:
            defer.returnValue([])

    def __init__(self, row=None):
        self._dirty = []
        self._fields = [col.name for col in self._table.columns]
        if self._table is None:
            raise NotImplementedError(
                "Children of DirtyContainer must override _table")
        if self._pk_column is None:
            self._pk_column = self._table.c.id
        self._pk = self._pk_column.name
        if row is not None:
            for f in self._fields:
                self[f] = row[f]
            self.mark_clean()

    def __setitem__(self, key, value):
        if key not in self._fields:
            raise KeyError("Invalid field for Container")
        if key in self.__dict__ and self.__dict__[key] == value:
            return
        self.__dict__[key] = value
        if key not in self._dirty:
            self._dirty.append(key)

    def __getitem__(self, key):
        if key not in self._fields:
            raise KeyError("Invalid field for Container")
        try:
            return self.__dict__[key]
        except KeyError:
            raise MissingData("Proxy Container not populated")

    def __contains__(self, key):
        return key in self.__dict__ and key in self._fields

    def complete_p(self):
        return reduce(operator.and_,
                      (key in self for key in self._fields))

    def dirty_p(self):
        return self._dirty is not []

    def dirty_fields(self):
        return self._dirty

    def dirty_dict(self):
        return {k: self.__dict__[k] for k in self._dirty}

    def dirty_pk_dict(self):
        """ PK is needed in dirty dict for multi-insert/update """
        dd = self.dirty_dict()
        dd[self._pk] = self[self._pk]
        # So, we need to satisfy the non-null constraint on insert,
        # even if we are disingenuously using upsert as a multi-update
        if 'key' in self:
            dd['key'] = self['key']
        if 'dk' in self:
            dd['dk'] = self['dk']
        if 'clock' in self:
            dd['clock'] = self['clock']
        return dd

    def update(self, d):
        for key in d.keys():
            self[key] = d[key]
        return self

    def needs_persist_p(self):
        return self.dirty_p()

    def mark_clean(self):
        self._dirty = []

    def merge(self, existing):
        return existing.update(self)

    def flatten(self):
        flat_dict = {
            k: self.__dict__[k] for k in self.__dict__.keys(
            ) if k in self._fields}
        for private in self._private_fields:
            if private in flat_dict:
                del flat_dict[private]
        for binary_field in ['id', 'listener_id', 'key']:
            if binary_field in flat_dict:
                flat_dict[binary_field] = hexlify(flat_dict[binary_field])
        return json.dumps(flat_dict, cls=BytesEncoder)

    @defer.inlineCallbacks
    def delete(self, conn=None):
        query = self._table.delete().where(
            self._pk_column == self[self._pk])
        if conn is None:
            rp = yield db.execute(query)
            rp.close()
        else:
            yield conn.execute(query)

    @defer.inlineCallbacks
    def save(self, conn=None):
        if self.dirty_p():
            log.msg("Updated {}".format(self))
            try:
                yield self.__class__.upsert(
                    self.dirty_pk_dict(), conn=conn)
            except Exception as e:
                raise e
            else:
                self.mark_clean()

    @classmethod
    @defer.inlineCallbacks
    def upsert(cls, upsertable, conn=None):
        if upsertable in [[], {}]:
            log.msg("Null Upsert")
            defer.returnValue(None)
        if isinstance(upsertable, list):
            # Problems if member dicts of list have different numbers
            # of fields, must separate
            sort_dict = {}
            for d in upsertable:
                hsh = ''.join(sorted(d.keys()))
                if hsh not in sort_dict:
                    sort_dict[hsh] = [d]
                else:
                    sort_dict[hsh].append(d)
            upsertable = sort_dict.values()
        else:
            upsertable = [upsertable]
        for i in upsertable:
            query = insert(cls._table, i)
            conflict_query = query.on_conflict_do_update(
                index_elements=[cls._table.c.id], set_={
                    a.name: a for a in query.excluded if a is not None})
            if conn is None:
                rp = yield db.execute(conflict_query)
                yield rp.close()
            else:
                yield conn.execute(conflict_query)

    def __repr__(self):
        if 'name' in self and self['name'] is not None:
            return "{}: {}".format(self.__class__.__name__,
                                   self['name'])
        return "{} #{}".format(self.__class__.__name__,
                               hexlify(self[self._pk]))


class LastSeenable(DirtyContainer):
    def missing_p(self):
        min_age = datetime.now(tz=UTC) - BEACON_LISTENER_TIMEOUT
        return self['last_seen'] < min_age

    def needs_persist_p(self):
        return DirtyContainer.needs_persist_p(self) and not self.missing_p()


class Listener(LastSeenable):
    _table = db.listeners

    def __init__(self, row=None):
        DirtyContainer.__init__(self, row=row)


class Beacon(LastSeenable):
    _table = db.beacons
    _private_fields = ['key', 'dk', 'clock']

    def __init__(self, row=None):
        DirtyContainer.__init__(self, row=row)

    def valid_dk(self, new_dk, new_clock):
        # Reset and calculate mask
        mask = 0xffffffff
        b_dk = self['dk']
        for i in range(self['clock']+1, new_clock+1):
            if i % DK0_INTERVAL == 0:
                b_dk, mask = evolve_dk(b_dk, mask, 0)
            if i % DK1_INTERVAL == 0:
                b_dk, mask = evolve_dk(b_dk, mask, 1)
        # If the beacon has been out of sight long enough that we have
        # no contemporary dk info
        if mask == 0:
            return True
        # Compare the incoming dk masked with our known uncertainty to
        # our generated value
        if b_dk != (new_dk & mask):
            return False
        return True
