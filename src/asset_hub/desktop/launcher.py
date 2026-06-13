"""桌面入口编排：预检可写性 → 迁移 → 起 server → 就绪后开窗。

与 cli/serve 完全独立，不复用 subprocess/PID/detach 那套。
"""

import os
import sys
from pathlib import Path

from asset_hub import migrate, runtime
from asset_hub.config import Settings
from asset_hub.desktop import dialogs, window
from asset_hub.desktop.server import BackgroundServer

_TITLE = "asset-hub"


def _bootstrap_settings() -> Settings:
    """frozen 下按 exe 同级解析 .env，并把最终 data_dir 写回 os.environ。

    关键：migrate/db.get_engine/storage/alembic env.py 内部都是裸 Settings()（按 cwd 找 .env）。
    若只把 _env_file 喂给这一个 Settings，预检放行的目录与真实 DB/迁移落点会 split-brain。
    写回 ASSET_HUB_DATA_DIR 让后续所有裸 Settings() 跟随同一落点（env 优先于 .env/default）。
    """
    if runtime.is_frozen():
        env_file = Path(sys.executable).resolve().parent / ".env"
        s = Settings(_env_file=str(env_file) if env_file.exists() else None)
        os.environ["ASSET_HUB_DATA_DIR"] = str(s.data_dir)
        return s
    return Settings()


def main() -> int:
    settings = _bootstrap_settings()

    # 预检 1：可写性（不可写不自动搬家，提示用户移动文件夹）
    if not runtime.is_writable_dir(settings.data_dir):
        dialogs.error_box(
            _TITLE,
            f"当前位置不可写：{settings.data_dir}\n\n"
            "请把整个 asset-hub 文件夹移动到文档/桌面等你有权限的位置后重新运行。\n"
            "（高级用户可在 exe 同级 .env 设 ASSET_HUB_DATA_DIR 指定别处。）",
        )
        return 1

    # 迁移：编程式 upgrade head
    try:
        migrate.run_migrations()
    except Exception as e:  # noqa: BLE001 — 顶层兜底，任何迁移异常都要弹框而非裸崩
        dialogs.error_box(_TITLE + " 迁移失败", f"数据库升级失败：\n{e}")
        return 1

    # 起服务
    server = BackgroundServer()
    server.start()
    if not server.wait_until_ready():
        dialogs.error_box(_TITLE, "后端启动超时，请重试或查看是否被防火墙拦截。")
        server.stop()
        return 1

    # 就绪后再开窗（避免首帧连接被拒）
    try:
        window.open_window(_TITLE, server.url)
    except Exception:  # noqa: BLE001 — pywebview/WebView2 缺失兜底
        dialogs.error_box(_TITLE, window.WEBVIEW2_HELP)
        return 1
    finally:
        server.stop()
    return 0
