from asset_hub.config import Settings


def test_default_ports():
    s = Settings()
    assert s.backend_port == 8000
    assert s.frontend_port == 5173


def test_env_override(monkeypatch):
    monkeypatch.setenv("ASSET_HUB_BACKEND_PORT", "9000")
    monkeypatch.setenv("ASSET_HUB_FRONTEND_PORT", "9001")
    s = Settings()
    assert s.backend_port == 9000
    assert s.frontend_port == 9001


def test_resolve_backend_host_dev_default():
    s = Settings()
    assert s.resolve_backend_host("dev") == "127.0.0.1"


def test_resolve_backend_host_prod_default():
    s = Settings()
    assert s.resolve_backend_host("prod") == "0.0.0.0"


def test_resolve_backend_host_explicit_override(monkeypatch):
    monkeypatch.setenv("ASSET_HUB_BACKEND_HOST", "192.168.1.10")
    s = Settings()
    assert s.resolve_backend_host("prod") == "192.168.1.10"
    assert s.resolve_backend_host("dev") == "192.168.1.10"


def test_pids_dir_under_data():
    s = Settings()
    assert str(s.pids_dir).endswith("pids")


def test_logs_dir_under_data():
    s = Settings()
    assert str(s.logs_dir).endswith("logs")
