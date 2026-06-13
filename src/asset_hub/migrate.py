"""启动时编程式数据库迁移（替代 frozen 环境下不可用的 `uv run alembic`）。"""

from pathlib import Path

from alembic import command
from alembic.config import Config

import asset_hub
from asset_hub.config import Settings


def _alembic_dir() -> Path:
    """alembic 脚本目录。包内资源：源码态 src/asset_hub/alembic、frozen 态 _MEIPASS/asset_hub/alembic，
    两者都等于"包目录 / alembic"。"""
    return Path(asset_hub.__file__).resolve().parent / "alembic"


def run_migrations() -> None:
    """把当前 DB 升到 head。不读相对 alembic.ini；script_location 按包目录解析，
    sqlalchemy.url 取 Settings().db_url（env.py 内会再次 Settings() 覆盖，一致）。"""
    cfg = Config()
    cfg.set_main_option("script_location", str(_alembic_dir()))
    cfg.set_main_option("sqlalchemy.url", Settings().db_url)
    command.upgrade(cfg, "head")
