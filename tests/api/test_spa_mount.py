import asset_hub.api.app as app_mod
import asset_hub.runtime as rt


def test_frontend_dist_is_absolute_from_resource_root():
    """_FRONTEND_DIST 应是基于 resource_root 的绝对路径，而非相对 cwd 的 Path('frontend/dist')。"""
    assert app_mod._FRONTEND_DIST == rt.resource_path("frontend", "dist")
    assert app_mod._FRONTEND_DIST.is_absolute()


def test_frozen_ignores_dev_mode(monkeypatch):
    """frozen 时即使 ASSET_HUB_MODE=dev，也不应被判为 dev（应挂 SPA）。"""
    monkeypatch.setattr(rt, "is_frozen", lambda: True)
    monkeypatch.setenv("ASSET_HUB_MODE", "dev")
    assert app_mod._compute_is_dev_mode() is False


def test_source_dev_mode_respected(monkeypatch):
    monkeypatch.setattr(rt, "is_frozen", lambda: False)
    monkeypatch.setenv("ASSET_HUB_MODE", "dev")
    assert app_mod._compute_is_dev_mode() is True
