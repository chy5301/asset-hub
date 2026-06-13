import urllib.request


def test_find_free_port_returns_bindable_int():
    from asset_hub.desktop.server import find_free_port

    port = find_free_port()
    assert isinstance(port, int) and 1024 < port < 65536


def test_background_server_serves_healthz():
    """真起一个后台 uvicorn，健康探测通过后访问 /api/healthz。"""
    from asset_hub.desktop.server import BackgroundServer

    srv = BackgroundServer()
    srv.start()
    try:
        assert srv.wait_until_ready(timeout=15.0) is True
        with urllib.request.urlopen(srv.url + "api/healthz", timeout=2.0) as r:
            assert r.status == 200
    finally:
        srv.stop()
