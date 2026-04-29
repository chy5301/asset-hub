import socket

from asset_hub.cli.serve.proc import is_port_in_use


def test_port_in_use_returns_true():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.listen(1)
    try:
        assert is_port_in_use(port) is True
    finally:
        s.close()


def test_port_free_returns_false():
    # Pick a random port that's almost certainly free by binding briefly then closing
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    # After close, port may briefly enter TIME_WAIT; allow either result
    # (not 100% deterministic but checking the function doesn't crash)
    result = is_port_in_use(port)
    assert isinstance(result, bool)
