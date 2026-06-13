"""原生错误提示框（无需 GUI 框架）。Windows 用 MessageBoxW；其他平台打印到 stderr。"""

import sys


def error_box(title: str, text: str) -> None:
    if sys.platform == "win32":
        import ctypes  # 惰性，避免非 win 平台告警

        ctypes.windll.user32.MessageBoxW(0, text, title, 0x10)  # MB_ICONERROR
    else:
        print(f"[{title}] {text}", file=sys.stderr)
