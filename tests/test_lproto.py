import pytest

from c3next import lproto


def test_ensure_header_bad_header():
    try:
        lproto.ensure_header_length(b'\x00')
    except Exception as e:
        assert isinstance(e, lproto.InvalidHeader)
        return
    assert False, "Failed to recognise invalid header"


@pytest.mark.parametrize("packet", [
    b'\x01\x00\x04Test', b'\xf0\x00\x04Test', b'\xf2\x00\x04Test'])
def test_get_packet_type_lte_4bit(packet):
    pt = lproto.get_packet_type(packet)
    assert pt < 16


def test_get_lid_too_big_does_exception():
    try:
        lproto.get_listener_id(b'\x00\x00\x05')
    except Exception as e:
        assert isinstance(e, lproto.InvalidListenerId)
        return
    assert False, "Failed to detect packet too short for lid"


def test_get_lid_null_does_exception():
    try:
        lproto.get_listener_id(b'\x00\x00\x00')
    except Exception as e:
        assert isinstance(e, lproto.InvalidListenerId)
        return
    assert False, "Failed to detect null lid"


@pytest.mark.parametrize("packet,correct_lid", [
    (b'\x00\x00\x01a', u'a'), (b'\x00\x00\x04Test', u'Test')])
def test_get_lid_is_correct(packet, correct_lid):
    l_id = lproto.get_listener_id(packet)
    assert l_id == correct_lid


@pytest.mark.parametrize("packet, correct_data", [
    (b'\x00\x00\x04Test', b''), (b'\x00\x00\x04Testa', b'a')])
def test_get_data_is_correct(packet, correct_data):
    data = lproto.get_data(packet)
    assert data == correct_data


def test_lid_munge_six_bytes_is_mac():
    """Listener id's with length of six are presumed to be mac addresses."""
    assert lproto.lid_munge(b'\x00\x01\x02\x03\x04\x05') == u'000102030405'


def test_lid_munge_lt_six_is_ascii():
    assert lproto.lid_munge(b'\x00\x01\x02\x03\x04') == u'\x00\x01\x02\x03\x04'


def test_lid_munge_pt_six_is_ascii():
    assert lproto.lid_munge(
        b'\x00\x01\x02\x03\x04\x05\x06') == u'\x00\x01\x02\x03\x04\x05\x06'
