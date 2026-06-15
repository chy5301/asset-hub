"""pywebview 原生窗口。webview 仅在 open_window 内惰性 import——
它是 [desktop] 可选依赖，后端 CI 不装；顶层 import 会让 Linux pytest 崩。"""

WEBVIEW2_HELP = (
    "asset-hub 需要 Microsoft Edge WebView2 Runtime 才能显示界面。\n"
    "请从 https://developer.microsoft.com/microsoft-edge/webview2/ 安装后重新运行。"
)


def open_window(title: str, url: str) -> None:
    import webview  # 惰性导入

    # WebView2 默认 ALLOW_DOWNLOADS=False，会把 DownloadStarting 静默 Cancel——
    # 导出（/api/export 返 Content-Disposition: attachment）在桌面版下不来文件（#42）。
    # 必须在 start 前开启，让原生保存对话框接管下载。
    webview.settings["ALLOW_DOWNLOADS"] = True

    # 尺寸依据前端实际布局（2026-06-14 窗口尺寸调查）：外壳容器 max-w-[1400px] + px-6
    # 两侧 → 内容满宽 ~1448px，故还原宽 1440 喂满主列、保筛选栏单行 + 看板双栏；
    # 看板 col-span-6 无响应式前缀、<1024 不折叠 → min 宽锁设计基线 1024；
    # 看板左图固定 height=400 + 顶部 chrome ~120 → 还原高 900 / min 高 700。
    webview.create_window(
        title,
        url,
        width=1440,
        height=900,
        min_size=(1024, 700),
        maximized=True,
    )
    webview.start()
