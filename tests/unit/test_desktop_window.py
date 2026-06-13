import importlib


def test_window_module_imports_without_pywebview():
    """window.py 顶层不得 import webview，否则 Linux 后端 CI 崩。"""
    mod = importlib.import_module("asset_hub.desktop.window")
    assert hasattr(mod, "open_window")
    assert isinstance(mod.WEBVIEW2_HELP, str) and "WebView2" in mod.WEBVIEW2_HELP


def test_dialogs_error_box_callable():
    from asset_hub.desktop import dialogs

    assert callable(dialogs.error_box)
