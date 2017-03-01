import six


FLAG = 0x7e
ESC = 0x7d
NEEDS_ESCAPE = [0x7d, 0x7e]


__all__ = ['HDLCInvalidFrame', 'hdlc_frame', 'hdlc_unframe']


class HDLCInvalidFrame(Exception):
    pass


def hdlc_frame(data):
    frame = bytearray()
    frame.append(FLAG)
    for byte in six.iterbytes(data):
        if byte in NEEDS_ESCAPE:
            frame.extend([ESC, byte & ~(1 << 5)])
        else:
            frame.append(byte)
    frame.append(FLAG)
    return bytes(frame)


def hdlc_unframe(frame):
    frame = bytearray(frame)
    if not frame[0] == frame[-1] == 0x7e:
        raise HDLCInvalidFrame("Missing flags")
    frame = frame.strip(b'\x7e')
    if FLAG in frame:
        raise HDLCInvalidFrame("Unescaped FLAG found")
    data = bytearray()
    i = 0
    while i < len(frame):
        if frame[i] == 0x7d:
            i += 1
            if i == len(frame):
                raise HDLCInvalidFrame("Incomplete escape sequence")
            data.append(frame[i] | (1 << 5))
        else:
            data.append(frame[i])
        i += 1
    return bytes(data)
