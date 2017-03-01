from c3next.hdlc import hdlc_frame
from c3next.listenerd import ListenerProtocol


def mock_proto_factory():
    proto = ListenerProtocol()

    class MockTransport(object):
        def __init__(self):
            self._output = []

        def write(self, data):
            self._output.append(data)

        def _spy(self):
            return self._output

        def getPeer(self):
            return "TestPeer"

    proto.transport = MockTransport()
    proto.connectionMade()
    return proto


def assert_nack(proto):
    assert proto.transport._spy() == [b'NACK']


def assert_ack(proto):
    assert proto.transport._spy() == [b'ACK']


def test_ignore_empty_frames():
    proto = mock_proto_factory()
    proto.dataReceived(b'\x7e\x7e\x7e')
    assert proto.transport._spy() == []


def test_short_packet_nack():
    proto = mock_proto_factory()
    proto.dataReceived(hdlc_frame(b'\x00'))
    assert_nack(proto)


def test_multiple_packets_per_call():
    proto = mock_proto_factory()
    multi_frame = hdlc_frame(
        b'\x00\x00\x04Test') + hdlc_frame(b'\x00\x00\x04Test')
    proto.dataReceived(multi_frame)
    assert proto.transport._spy() == [b'ACK', b'ACK']


def test_invalid_hdlc_does_nack():
    proto = mock_proto_factory()
    proto.dataReceived(b'\x7e\x7d\x7e')
    assert_nack(proto)


def test_ack_keepalive():
    proto = mock_proto_factory()
    proto.dataReceived(hdlc_frame(b'\x00\x00\x04Test'))
    assert_ack(proto)


def test_invalid_packet_type_does_nack():
    proto = mock_proto_factory()
    proto.dataReceived(hdlc_frame(b'\xff\x00\x00'))
    assert_nack(proto)


def test_short_sec_packet_does_nack():
    proto = mock_proto_factory()
    proto.dataReceived(hdlc_frame(b'\x02\x00\x04Test'))
    assert_nack(proto)


def test_invalid_mac_check_does_ack():
    proto = mock_proto_factory()
    proto.dataReceived(hdlc_frame(
        b'\x02\x00\x04Test'+39*b'\x00'))
    assert_ack(proto)


def test_long_l_id_length_does_nack():
    proto = mock_proto_factory()
    proto.dataReceived(hdlc_frame(b'\x00\x00\xffTest'))
    assert_nack(proto)


# Cannot be determined reliably due to protocol limitations
# def test_short_l_id_len_does_nack():
#     proto = proto = mock_proto_factory()
#     proto.dataReceived(hdlc_frame(b'\x00\x00\x03Test'))
#     assert_nack(proto)
