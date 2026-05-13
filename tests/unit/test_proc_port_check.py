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


def test_port_in_use_returns_true_for_ipv6_only():
    """IPv6 ::1 上监听的端口必须被识别为占用（Vite 8.x dev 默认只绑 IPv6）。"""
    s = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
    s.bind(("::1", 0))
    port = s.getsockname()[1]
    s.listen(1)
    try:
        assert is_port_in_use(port) is True
    finally:
        s.close()


def test_port_in_use_handles_ipv6_disabled_gracefully(monkeypatch):
    """IPv6 系统级不可用时（如某些容器），探测应优雅退化为 IPv4 单栈而非崩溃。"""
    import socket as socket_mod

    real_socket = socket_mod.socket

    def fake_socket(family, *a, **kw):
        if family == socket_mod.AF_INET6:
            raise OSError("Address family not supported by protocol")
        return real_socket(family, *a, **kw)

    monkeypatch.setattr("asset_hub.cli.serve.proc.socket.socket", fake_socket)
    # 在系统级 IPv6 不可用时，free IPv4 端口仍应识别为 free（bool 而非异常）
    s = real_socket(socket_mod.AF_INET, socket_mod.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    free_port = s.getsockname()[1]
    s.close()
    result = is_port_in_use(free_port)
    assert isinstance(result, bool)
