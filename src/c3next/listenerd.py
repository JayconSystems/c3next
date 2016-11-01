from __future__ import division
from __future__ import absolute_import
from __future__ import print_function

import hmac
import math
import struct
import time
from datetime import datetime
from binascii import hexlify

from Crypto.Hash import CMAC
from Crypto.Cipher import AES

import sqlalchemy as sa

from twisted.application.internet import UDPServer
from twisted.application.service import Service
from twisted.internet import protocol, reactor, defer
from twisted.python import log

from c3next import db
from c3next.config import MASTER_KEY, DK0_INTERVAL, DK1_INTERVAL

class PacketType:
    KEEPALIVE = 0
    DATA = 1
    SECURE = 2

def derive_key(b_id):
    cmac = CMAC.new(MASTER_KEY, ciphermod=AES)
    cmac.update(b_id)
    return cmac.digest()

def validate_dk(b, new_dk, new_clock):
    # Reset and calculate mask
    mask = 0xffffffff
    b_dk = b.dk
    for i in range(b.clock+1, new_clock+1):
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
    if b.dk != (new_dk & mask):
        print(
"""Failed DK:\n
\tLocal : {:032b}
\tBeacon: {:032b}
\tMask  : {:32b}""".format(b.dk, new_dk, mask))
        return False
    return True

def evolve_dk(dk, mask, num):
    # Evolve the DK. Same algo as the "beacon", but we know we'll
    # be masking the unknown bits, so shift in zeros
    h, l = dk >> 16, dk & 0x0000ffff
    m_h, m_l = mask >> 16, mask & 0x0000ffff
    if num == 0:
        l = (l << 1) & 0xffff
        m_l = m_l << 1 & 0xffff
        if num == 1:
            h = h << 1 & 0xffff
            m_h = m_h << 1
    dk = (h << 16) | l & 0xffff
    mask = (m_h << 16) | m_l
    return (dk, mask)

class ListenerProtocol(protocol.DatagramProtocol):

    def datagramReceived(self, packet, host_port_tup):
        self.peer = host_port_tup
        d = self.processPacket(packet)
        def do_ack(result):
            self.transport.write(b"ACK", self.peer)
        def _failed(result):
            self.transport.write(b'NACK', self.peer)
            log.err(result)
        d.addCallbacks(do_ack, _failed)
        log.msg("Processed")

    @defer.inlineCallbacks
    def processPacket(self, packet):
        HEADER_LENGTH=3
        timestamp = datetime.now()
        header, _, hostname_len = struct.unpack("BBB", packet[:HEADER_LENGTH])
        version = header >> 4
        packet_type = header & 0x0f

        l_id = packet[HEADER_LENGTH:HEADER_LENGTH+hostname_len]

        l = yield db.execute(db.listeners.select().where(
            db.listeners.c.id == l_id), fetchAll=False)

        if not l:
            log.msg("New Listener: {}".format(hexlify(l_id)))
            yield db.execute(db.listeners.insert().values({
                'id': l_id,
                'name': 'Listener {}'.format(hexlify(l_id))}),
                             returnsData=False)
        else:
            yield db.execute(db.listeners.update().where(
                db.listeners.c.id == l_id).values(
                    last_seen=sa.func.now()), returnsData=False)

        if packet_type == PacketType.KEEPALIVE:
            log.msg(u"Keepalive from {}".format(l_id))
            defer.returnValue(None)
        elif packet_type != PacketType.SECURE:
            log.msg(u"Deprecated/Unknown packet from: {}".format(l_id))
            defer.returnValue(None)

        data = packet[HEADER_LENGTH+hostname_len:]
        (b_id, nonce, msg, tag, distance, variance) = struct.unpack(
            "<6s 16s 9s 4s H H", data)
        distance = distance / 100
        variance = variance / 100

        b = yield db.execute(
            db.beacons.select().where(db.beacons.c.id == b_id),
            fetchAll=False)
        if not b:
            b_key = derive_key(b_id)
        else:
            b_key = b['key']

        cipher = AES.new(b_key, AES.MODE_EAX, nonce, mac_len=4)
        cipher.update(b_id)

        try:
            plaintext = cipher.decrypt_and_verify(msg, tag)
        except ValueError as decrypt_verify_error:
            log.msg(u"Packet: {}\n\
                    \tListener ID: {}\n\
                    \tBeacon ID: {}\n\
                    \tMessage:{}\n\
                    \tTag: {}\n".format(hexlify(packet),
                                        hexlify(l_id),
                                        hexlify(b_id),
                                        hexlify(msg),
                                        hexlify(tag)))

            log.err("Payload Decipher Error: {}".format(
                decrypt_verify_error))
            defer.returnValue(None)

        (clock, dk, flags) = struct.unpack("<IIB", plaintext)

        if not b:
            origin = time.time() - clock
            origin = origin if origin > 0 else 0.0
            b = {'id': b_id,
                 'listener_id': l_id,
                 'name': "Beacon {}".format(hexlify(b_id)),
                 'key': b_key,
                 'clock': clock,
                 'dk': dk,
                 'clock_origin': origin}
            yield db.execute(db.beacons.insert().values(b),
                             returnsData=False)
            defer.returnValue(None)

        if b['clock'] and (clock < b['clock']):
            # Reject old clock values
            log.warning("Attempted replay of {}@{}".format(b['name'], clock))
            defer.returnValue(None)

        if validate_dk(b, dk, clock):
            yield db.execute(db.beacons.update().where(
                db.beacons.c.id == b_id).values({
                    'dk': dk,
                    'clock': clock,
                    'last_seen': sa.func.now()
                }), returnsData=False)
            log.msg("""\n
            \tListener ID: {}
            \tBeacon ID: {}
            \t\tClock: {} (Skew: {:.2f}s)
            \t\tDK: {}
            \t\tFlags: {}
            \tDistance: {}m
            \tVariance: {} ({:.2}m)""".format(
                    hexlify(l_id),
                    hexlify(b_id),
                    clock, time.time() - (b['clock_origin'] + clock), dk,
                    flags, distance, variance,
                    math.sqrt(variance)*3))
        else:
            log.warn("Invalid DK")
