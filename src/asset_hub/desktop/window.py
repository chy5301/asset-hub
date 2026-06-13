"""pywebview 原生窗口。webview 仅在 open_window 内惰性 import——
它是 [desktop] 可选依赖，后端 CI 不装；顶层 import 会让 Linux pytest 崩。"""

WEBVIEW2_HELP = (
    "asset-hub 需要 Microsoft Edge WebView2 Runtime 才能显示界面。\n"
    "请从 https://developer.microsoft.com/microsoft-edge/webview2/ 安装后重新运行。"
)


def open_window(title: str, url: str) -> None:
    import webview  # 惰性导入

    webview.create_window(title, url)
    webview.start()
