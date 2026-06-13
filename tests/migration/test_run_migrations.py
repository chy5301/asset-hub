"""migrate.run_migrations() 编程式 upgrade head：把旧版本库升到 head。"""

import sys
from unittest.mock import MagicMock, patch

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect


def _clear_env_cache():
    for key in list(sys.modules.keys()):
        if "asset_hub.alembic" in key or key.endswith(".env"):
            del sys.modules[key]


@pytest.fixture
def v3_db(tmp_path):
    """临时库先 upgrade 到 v3 head（2d589d84e584），模拟"旧版本数据库"。"""
    db_path = tmp_path / "asset_hub.db"
    db_url = f"sqlite:///{db_path}"
    mock_settings = MagicMock()
    mock_settings.db_url = db_url

    cfg = Config("alembic.ini")
    cfg.set_main_option("script_location", "src/asset_hub/alembic")
    cfg.set_main_option("sqlalchemy.url", db_url)

    _clear_env_cache()
    with patch("asset_hub.config.Settings", return_value=mock_settings):
        command.upgrade(cfg, "2d589d84e584")
    return db_path, db_url, mock_settings


def test_run_migrations_upgrades_old_db_to_head(v3_db):
    from asset_hub import migrate

    db_path, db_url, mock_settings = v3_db
    engine = create_engine(db_url)
    cols_before = {c["name"] for c in inspect(engine).get_columns("assets")}
    assert "brand" not in cols_before  # v3 尚无 v4 的 brand 列

    _clear_env_cache()
    with patch("asset_hub.config.Settings", return_value=mock_settings):
        migrate.run_migrations()

    engine = create_engine(db_url)
    cols_after = {c["name"] for c in inspect(engine).get_columns("assets")}
    assert "brand" in cols_after  # run_migrations 已把库升到含 v4 的 head


def test_run_migrations_idempotent_on_head(v3_db):
    """已在 head 再跑一次不报错（no-op）。"""
    from asset_hub import migrate

    _, _, mock_settings = v3_db
    _clear_env_cache()
    with patch("asset_hub.config.Settings", return_value=mock_settings):
        migrate.run_migrations()
        migrate.run_migrations()  # 第二次 no-op，不抛
