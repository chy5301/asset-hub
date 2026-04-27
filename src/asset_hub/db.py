"""Engine + create_all 兜底。

M2c-3 起引入 alembic 管理已有 DB 的 schema 演进。新部署仍可用
create_all 直接拉起最新 schema；已有 DB 必须用 `alembic upgrade head`
应用迁移。两条路径产生相同最终 schema。
"""

from sqlalchemy import Engine
from sqlmodel import SQLModel, create_engine

from asset_hub.config import Settings

_engine: Engine | None = None


def get_engine(settings: Settings | None = None) -> Engine:
    global _engine
    if _engine is None:
        if settings is None:
            settings = Settings()
        settings.data_dir.mkdir(parents=True, exist_ok=True)
        _engine = create_engine(settings.db_url)
        SQLModel.metadata.create_all(_engine)
    return _engine


def reset_engine() -> None:
    global _engine
    _engine = None
