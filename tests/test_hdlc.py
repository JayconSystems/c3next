import six
from c3next.hdlc import hdlc_frame, hdlc_unframe, HDLCInvalidFrame


def test_frame_has_flags():
    frame = hdlc_frame(b'Hello World')
    print(frame)
    assert six.indexbytes(frame, 0) == 0x7e
    assert six.indexbytes(frame, -1) == 0x7e


def test_frame_no_internal_flags():
    frame = hdlc_frame(b'\x7e')
    assert b'\x7e' not in frame[1:-1]


def test_frame_flag_escaped():
    frame = hdlc_frame(b'\x7e')
    assert frame == b'\x7e\x7d\x5e\x7e'


def test_frame_esc_escaped():
    frame = hdlc_frame(b'\x7d')
    assert frame == b'\x7e\x7d\x5d\x7e'


def test_unframe_strips_extra_flags():
    data = hdlc_unframe(b'\x7e\x7e!\x7e')
    assert data == b'!'


def test_unframe_invalid_escape():
    try:
        hdlc_unframe(b'\x7e\x7d\x7e')
    except Exception as e:
        assert isinstance(e, HDLCInvalidFrame)
        return
    assert False, "Failed to recognise invalid escape"


def test_unframe_no_flags_raises_exception():
    try:
        hdlc_unframe(b'No Flags')
    except Exception as e:
        assert isinstance(e, HDLCInvalidFrame)
        return
    assert False, "Failed to raise InvalidPacket on FLAG-less packet"


def test_unframe_internal_flag_raises_exception():
    try:
        hdlc_unframe(b'Unescaped \x7e in packet')
    except Exception as e:
        assert isinstance(e, HDLCInvalidFrame)
        return
    assert False, "Failed to raise InvalidPacket on internal FLAG"


def test_unframe_removes_flags():
    assert hdlc_unframe(b'\x7e\x7e') == b''
    assert hdlc_unframe(b'\x7e!\x7e') == b'!'


def test_unframe_unescapes_flag():
    data = hdlc_unframe(b'\x7e\x7d\x5e\x7e')
    assert data == b'\x7e'


def test_unframe_unescapes_esc():
    data = hdlc_unframe(b'\x7e\x7d\x5d\x7e')
    assert data == b'\x7d'


def test_frame_unframe_are_opposites():
    hard_packet = b'A hard packet contains these \x7e\x7d'
    assert hdlc_unframe(hdlc_frame(hard_packet)) == hard_packet
