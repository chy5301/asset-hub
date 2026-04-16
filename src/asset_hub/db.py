# src/asset_hub/db.py
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
