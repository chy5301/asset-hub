"""launcher.main() 预检路径测试：mock 掉 server/window，只验证 abort 逻辑。"""

import os
from unittest.mock import MagicMock

from asset_hub.desktop import launcher


def test_main_aborts_when_data_dir_not_writable(monkeypatch):
    """不可写 → 弹 error_box + return 1，不走迁移。"""
    calls: dict = {}
    monkeypatch.setattr(launcher.runtime, "is_writable_dir", lambda p: False)
    monkeypatch.setattr(
        launcher.dialogs,
        "error_box",
        lambda title, text: calls.__setitem__("box", (title, text)),
    )
    monkeypatch.setattr(
        launcher.migrate,
        "run_migrations",
        lambda: calls.__setitem__("migrate", True),
    )

    rc = launcher.main()

    assert rc == 1
    assert "box" in calls  # 弹了提示
    assert "migrate" not in calls  # 没往下走到迁移/起服务


def test_main_aborts_when_migration_fails(monkeypatch):
    """迁移异常 → 弹 error_box（含异常信息） + return 1，不起 server。"""
    calls: dict = {}
    monkeypatch.setattr(launcher.runtime, "is_writable_dir", lambda p: True)

    def _boom():
        raise RuntimeError("migration broke")

    monkeypatch.setattr(launcher.migrate, "run_migrations", _boom)
    monkeypatch.setattr(
        launcher.dialogs,
        "error_box",
        lambda title, text: calls.__setitem__("box", (title, text)),
    )
    # 确保不会真去起 server
    monkeypatch.setattr(
        launcher,
        "BackgroundServer",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("不应起 server")),
    )

    rc = launcher.main()
    assert rc == 1
    assert "migration broke" in calls["box"][1]


def test_bootstrap_settings_frozen_propagates_env_to_bare_settings(
    monkeypatch, tmp_path
):
    """frozen + exe 同级 .env 设 ASSET_HUB_DATA_DIR → 写回 os.environ，
    后续裸 Settings() 跟随（修 split-brain：预检与真实落点一致）。"""
    from asset_hub.config import Settings

    custom = tmp_path / "portable-data"
    exe = tmp_path / "asset-hub.exe"
    exe.write_text("")
    (tmp_path / ".env").write_text(f"ASSET_HUB_DATA_DIR={custom}\n")

    monkeypatch.setattr(launcher.runtime, "is_frozen", lambda: True)
    monkeypatch.setattr(launcher.sys, "executable", str(exe))
    monkeypatch.delenv("ASSET_HUB_DATA_DIR", raising=False)

    s = launcher._bootstrap_settings()

    assert s.data_dir == custom
    assert os.environ["ASSET_HUB_DATA_DIR"] == str(custom)
    assert Settings().data_dir == custom  # 后续裸 Settings() 跟随同一落点


def _make_mock_server(monkeypatch, *, ready: bool = True) -> MagicMock:
    """构造 mock BackgroundServer，注入到 launcher 模块。"""
    mock_server = MagicMock()
    mock_server.wait_until_ready.return_value = ready
    mock_server.url = "http://127.0.0.1:19999/"
    mock_cls = MagicMock(return_value=mock_server)
    monkeypatch.setattr(launcher, "BackgroundServer", mock_cls)
    monkeypatch.setattr(launcher.runtime, "is_writable_dir", lambda p: True)
    monkeypatch.setattr(launcher.migrate, "run_migrations", lambda: None)
    return mock_server


def test_main_aborts_when_server_startup_timeout(monkeypatch):
    """server 超时 → 弹 error_box + stop + return 1。"""
    calls: dict = {}
    mock_server = _make_mock_server(monkeypatch, ready=False)
    monkeypatch.setattr(
        launcher.dialogs,
        "error_box",
        lambda title, text: calls.__setitem__("box", (title, text)),
    )

    rc = launcher.main()

    assert rc == 1
    assert "超时" in calls["box"][1]
    mock_server.stop.assert_called_once()


def test_main_aborts_when_window_fails(monkeypatch):
    """open_window 异常 → 弹 WEBVIEW2_HELP + stop + return 1。"""
    calls: dict = {}
    _make_mock_server(monkeypatch, ready=True)
    monkeypatch.setattr(
        launcher.window,
        "open_window",
        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("no webview")),
    )
    monkeypatch.setattr(
        launcher.dialogs,
        "error_box",
        lambda title, text: calls.__setitem__("box", (title, text)),
    )

    rc = launcher.main()

    assert rc == 1
    assert "WebView2" in calls["box"][1]


def test_main_returns_zero_on_success(monkeypatch):
    """全链路成功 → return 0，finally 调 stop。"""
    mock_server = _make_mock_server(monkeypatch, ready=True)
    monkeypatch.setattr(launcher.window, "open_window", lambda *a, **k: None)

    rc = launcher.main()

    assert rc == 0
    mock_server.stop.assert_called_once()
