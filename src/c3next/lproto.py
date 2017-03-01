import enum
from binascii import hexlify

import six

HEADER_LENGTH = 3


class PacketType(enum.IntEnum):
    KEEPALIVE = 0
    DATA = 1
    SECURE = 2


class LProtoError(Exception):
    pass


class InvalidHeader(LProtoError):
    pass


class InvalidListenerId(LProtoError):
    pass


def ensure_header_length(packet):
    if len(packet) < HEADER_LENGTH:
        raise InvalidHeader
    return


def get_packet_type(packet):
    pt = six.indexbytes(packet, 0) & 0x0f
    if pt not in list(PacketType):
        raise InvalidHeader("Bad Packet Type: {}".format(pt))
    return pt


def lid_munge(l_id):
    if len(l_id) == 6:
        l_id = hexlify(l_id)
    return l_id.decode('latin-1')


def get_listener_id_len(packet):
    return six.indexbytes(packet, 2)


def get_listener_id(packet):
    lid_len = get_listener_id_len(packet)
    if len(packet[HEADER_LENGTH:]) < lid_len:
        raise InvalidListenerId(
            "Packet length ({}) is less than l_id length ({})".format(
                len(packet)-HEADER_LENGTH, lid_len))
    if lid_len == 0:
        raise InvalidListenerId("Zero length l_id is not supported")
    return lid_munge(packet[HEADER_LENGTH:HEADER_LENGTH+lid_len])


def get_data(packet):
    lid_len = get_listener_id_len(packet)
    return packet[HEADER_LENGTH+lid_len:]
