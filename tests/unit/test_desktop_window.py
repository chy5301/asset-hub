import importlib
import sys
import types


def test_window_module_imports_without_pywebview():
    """window.py 顶层不得 import webview，否则 Linux 后端 CI 崩。"""
    mod = importlib.import_module("asset_hub.desktop.window")
    assert hasattr(mod, "open_window")
    assert isinstance(mod.WEBVIEW2_HELP, str) and "WebView2" in mod.WEBVIEW2_HELP


def test_open_window_enables_downloads(monkeypatch):
    """open_window 必须开 ALLOW_DOWNLOADS——否则 WebView2 默认静默取消下载，
    桌面便携版导出（/api/export 返回 Content-Disposition: attachment）下不来文件（#42）。"""
    fake_webview = types.ModuleType("webview")
    fake_webview.settings = {"ALLOW_DOWNLOADS": False}
    fake_webview.create_window = lambda *a, **k: None
    fake_webview.start = lambda *a, **k: None
    monkeypatch.setitem(sys.modules, "webview", fake_webview)

    from asset_hub.desktop.window import open_window

    open_window("t", "http://127.0.0.1:1234/")

    assert fake_webview.settings["ALLOW_DOWNLOADS"] is True


def test_dialogs_error_box_stderr_fallback(monkeypatch, capsys):
    """强制走 stderr 路径（monkeypatch sys.platform），验证输出。"""
    from asset_hub.desktop.dialogs import error_box

    monkeypatch.setattr("sys.platform", "linux")
    error_box("TestTitle", "TestMsg")
    captured = capsys.readouterr()
    assert "TestTitle" in captured.err
    assert "TestMsg" in captured.err
