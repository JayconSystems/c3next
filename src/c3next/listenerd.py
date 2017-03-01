from __future__ import division
from __future__ import absolute_import
from __future__ import print_function

import struct
import time
from binascii import hexlify
from datetime import datetime
from pytz import UTC

from Crypto.Cipher import AES

import sqlalchemy as sa

from twisted.application import internet
from twisted.internet import protocol, defer
from twisted.python import log

from c3next import db, lproto
from c3next.hdlc import hdlc_unframe, HDLCInvalidFrame
from c3next.models import Listener, Beacon
from c3next.util import derive_key

HEADER_LENGTH = 3

LISTENERS = {}
BEACONS = {}

TABLE_NAME_OBJ_MAP = {'listeners': Listener,
                      'beacons': Beacon}


class PacketType:
    KEEPALIVE = 0
    DATA = 1
    SECURE = 2


class ListenerProtocol(protocol.Protocol):

    def __init__(self):
        self._buf = bytearray()

    def connectionMade(self):
        self._peer = self.transport.getPeer()

    def dataReceived(self, data):
        data = bytearray(data)
        for byte in data:
            self._buf.append(byte)
            if byte == 0x7e:
                if len(self._buf) > 1:
                    try:
                        packet = hdlc_unframe(self._buf)
                    except HDLCInvalidFrame as e:
                        log.err("Invalid HDLC from {}: {}".format(
                            self._peer, e))
                        self.transport.write(b'NACK')
                        self._buf = bytearray()
                        return
                    if len(packet) > 0:
                        self.do_packet(packet)
                        self._buf = bytearray()

    def do_packet(self, packet):
        try:
            lproto.ensure_header_length(packet)
            packet_type = lproto.get_packet_type(packet)
            l_id = lproto.get_listener_id(packet)
        except lproto.LProtoError as e:
            self.transport.write(b'NACK')
            log.err(u"Invalid packet from {}: {}".format(
                self._peer, e))
            return

        if l_id not in LISTENERS:
            l = Listener()
            l['id'] = l_id
            LISTENERS[l_id] = l
        else:
            l = LISTENERS[l_id]
        l['last_seen'] = datetime.now(tz=UTC)
        if packet_type == PacketType.KEEPALIVE:
            self.transport.write(b'ACK')
            return
        elif packet_type == PacketType.DATA:
            # log.msg(u"Skipping iBeacon format, currently unimplemented.")
            self.transport.write(b'ACK')
            return

        elif packet_type == PacketType.SECURE:
            self.do_secure(l_id, packet)
            return

    def do_secure(self, l_id, packet):
        data = lproto.get_data(packet)
        if len(data) != 39:
            log.err(u"Invalid data in packet from: {} @ {}".format(
                l_id, self._peer))
            self.transport.write(b'NACK')
            return

        # After this point, any errors are not from the listener, but
        # the beacon. So we ACK the packet now. This may avoid an
        # oracle attack by hiding the timing of the cryptography
        # options that follow
        self.transport.write(b'ACK')

        (b_id, nonce, msg, tag, distance, variance) = struct.unpack(
            "<6s 16s 9s 4s H H", data)
        distance = distance / 100
        variance = variance / 100

        if b_id not in BEACONS:
            b = Beacon()
            b['id'] = hexlify(b_id)
            BEACONS[b_id] = b
        else:
            b = BEACONS[b_id]

        if 'key' in b and b['key'] is not None:
            b_key = b['key']
        else:
            b_key = derive_key(b_id)

        cipher = AES.new(b_key, AES.MODE_EAX, nonce, mac_len=4)
        cipher.update(b_id)

        try:
            plaintext = cipher.decrypt_and_verify(msg, tag)
        except ValueError as decrypt_verify_error:
            if 'rejected_mac' in b:
                b['rejected_mac'] += 1
            log.err("Payload Decipher Error: {}".format(
                decrypt_verify_error))
            # Packet it ACKd even if decrypt is unsuccessful, because
            # this sort of error can not be caused by the listener
            return
        b['key'] = b_key

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
            if 'rejected_replay' in b:
                b['rejected_replay'] += 1
            log.err("Attempted replay of {}@{}".format(b['name'], clock))
            return

        if b.valid_dk(dk, clock):
            b.update({'dk': dk,
                      'clock': clock,
                      'listener_id': l_id,
                      'last_seen': datetime.now(tz=UTC)})
        else:
            if 'rejected_dk' in b:
                b['rejected_dk'] += 1
            else:
                b['rejected_dk'] = 1
            log.msg("Invalid DK")


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
