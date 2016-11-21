from __future__ import division
from __future__ import absolute_import
from __future__ import print_function

import struct
import time
from datetime import datetime
from pytz import UTC

from Crypto.Cipher import AES

import sqlalchemy as sa

from twisted.application import internet
from twisted.internet import protocol, defer
from twisted.python import log

from c3next import db
from c3next.models import Listener, Beacon
from c3next.util import derive_key


LISTENERS = {}
BEACONS = {}

TABLE_NAME_OBJ_MAP = {'listeners': Listener,
                      'beacons': Beacon}


class PacketType:
    KEEPALIVE = 0
    DATA = 1
    SECURE = 2


class ListenerProtocol(protocol.DatagramProtocol):

    def datagramReceived(self, packet, peer):
        HEADER_LENGTH = 3
        header, _, hostname_len = struct.unpack("BBB", packet[:HEADER_LENGTH])
        packet_type = header & 0x0f

        # Create / Fetch eventual consistency listener proxy
        l_id = packet[HEADER_LENGTH:HEADER_LENGTH+hostname_len]
        if l_id not in LISTENERS:
            l = Listener()
            l['id'] = l_id
            LISTENERS[l_id] = l
        else:
            l = LISTENERS[l_id]
        l['last_seen'] = datetime.now(tz=UTC)
        if packet_type == PacketType.KEEPALIVE:
            self.transport.write("ACK", peer)
            return
        elif packet_type != PacketType.SECURE:
            log.err(u"Deprecated/Unknown packet from: {}".format(l_id))
            self.transport.write("NACK", peer)
            return

        data = packet[HEADER_LENGTH+hostname_len:]
        (b_id, nonce, msg, tag, distance, variance) = struct.unpack(
            "<6s 16s 9s 4s H H", data)
        distance = distance / 100
        variance = variance / 100

        if b_id not in BEACONS:
            b = Beacon()
            b['id'] = b_id
            BEACONS[b_id] = b
        else:
            b = BEACONS[b_id]

        if 'key' in b and b['key'] is not None:
            b_key = b['key']
        else:
            b['key'] = b_key = derive_key(b_id)

        cipher = AES.new(b_key, AES.MODE_EAX, nonce, mac_len=4)
        cipher.update(b_id)

        try:
            plaintext = cipher.decrypt_and_verify(msg, tag)
        except ValueError as decrypt_verify_error:
            b['rejected_mac'] += 1
            log.err("Payload Decipher Error: {}".format(
                decrypt_verify_error))
            return

        (clock, dk, flags) = struct.unpack("<IIB", plaintext)

        if 'clock' not in b:
            # New beacons cannot be verified for relay or DK. Trust on
            # first use
            origin = time.time() - clock
            origin = origin if origin > 0 else 0.0
            b.update({'listener_id': l_id,
                      'name': "{}".format(b),
                      'clock': clock,
                      'dk': dk,
                      'clock_origin': origin,
                      'last_seen': datetime.now(tz=UTC)})
            return

        if b['clock'] and (clock < b['clock']):
            # Reject old clock values
            b['rejected_replay'] += 1
            log.err("Attempted replay of {}@{}".format(b['name'], clock))
            self.transport.write("ACK", peer)
            return

        if b.valid_dk(dk, clock):
            b.update({'dk': dk,
                      'clock': clock,
                      'last_seen': datetime.now(tz=UTC)})
        else:
            b['rejected_dk'] += 1
            log.msg("Invalid DK")
        self.transport.write("ACK", peer)


class DataPersistanceService(internet.TimerService):
    def __init__(self, interval):
        self.serial = 0
        internet.TimerService.__init__(self, interval, self._run)

    # @defer.inlineCallbacks
    # def _resync_listeners(self):
    #     global LISTENERS
    #     result = yield self._conn.execute(db.listeners.select())
    #     result = yield result.fetchall()
    #     new_cache = {r['id']: Listener(row=r) for r in result}
    #     for k in new_cache.keys():
    #         if (k in LISTENERS and
    #             LISTENERS[k]['last_seen'] > new_cache[k]['last_seen']):
    #                 new_cache[k] = LISTENERS[k]
    #         LISTENERS = new_cache

    # @defer.inlineCallbacks
    # def _resync_beacons(self):
    #     global BEACONS
    #     result = yield self._conn.execute(db.beacons.select())
    #     result = yield result.fetchall()
    #     new_cache = {r['id']: Beacon(row=r) for r in result}
    #     for k in new_cache.keys():
    #         if (k in BEACONS and
    #             BEACONS[k]['last_seen'] > new_cache[k]['last_seen']):
    #                 new_cache[k] = BEACONS[k]
    #         BEACONS = new_cache

    # def _resync(self):
    #     return defer.DeferredList([self._resync_listeners(),
    #                                self._resync_beacons()])

    @defer.inlineCallbacks
    def _run(self):
        log.msg("Running persist {}".format(self.serial))
        self._conn = yield db.get_connection()
        # if self.serial % SYNC_INTERVAL == 0:
        #     self.serial =+ 1
        #     t1 = time.time()
        #     yield self._resync()
        #     t2 = time.time()
        #     log.msg("Resync Completed in {} seconds".format(t2 - t1))

        # Listeners
        # Get listeners missing from cache
        cur = yield self._conn.execute(sa.select([db.listeners.c.id]))
        rp = yield cur.fetchall()
        missing_from_cache_id = [r for (r,) in rp if r not in LISTENERS]
        missing_from_cache = yield Listener.fetch_many(
            missing_from_cache_id, conn=self._conn)
        missing_dict = {r['id']: r for r in missing_from_cache}
        LISTENERS.update(missing_dict)

        # Send Updates
        dirty_listeners = [
            a.dirty_pk_dict() for a in LISTENERS.values(
            ) if a.needs_persist_p()]
        if dirty_listeners is not []:
            yield Listener.upsert(dirty_listeners, conn=self._conn)

        # Beacons
        # Get beacons missing from cache
        cur = yield self._conn.execute(sa.select([db.beacons.c.id]))
        rp = yield cur.fetchall()
        missing_from_cache_id = [r for (r,) in rp if r not in BEACONS]
        missing_from_cache = yield Beacon.fetch_many(
            missing_from_cache_id, conn=self._conn)
        missing_dict = {r['id']: r for r in missing_from_cache}
        BEACONS.update(missing_dict)

        # Send Updates
        dirty_beacons = [
            a.dirty_pk_dict() for a in BEACONS.values() if a.needs_persist_p()]
        if dirty_beacons is not []:
            yield Beacon.upsert(dirty_beacons, conn=self._conn)

        yield self._conn.close()
        self.serial += 1
