"""v3 migration 测：upgrade 加 model 列 + ix_assets_model 索引；downgrade 回退干净。"""

import sys
from unittest.mock import MagicMock, patch

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect


def _make_cfg(db_path):
    """构建 alembic Config，指向指定 DB 路径。"""
    cfg = Config("alembic.ini")
    cfg.set_main_option("script_location", "src/asset_hub/alembic")
    cfg.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")
    return cfg


def _clear_env_cache():
    """清缓存让 alembic 重新执行 env.py，使 patch 生效。"""
    for key in list(sys.modules.keys()):
        if "asset_hub.alembic" in key or key.endswith(".env"):
            del sys.modules[key]


@pytest.fixture
def v2_db(tmp_path):
    """临时数据库，upgrade 到 v2 head（v3 之前）。

    env.py 里 Settings() 会覆盖 sqlalchemy.url，所以 mock Settings 让它返回 tmp 路径。
    """
    db_path = tmp_path / "asset_hub.db"
    db_url = f"sqlite:///{db_path}"

    mock_settings = MagicMock()
    mock_settings.db_url = db_url

    cfg = _make_cfg(db_path)

    _clear_env_cache()
    with patch("asset_hub.config.Settings", return_value=mock_settings):
        command.upgrade(
            cfg, "2b6e5509aeef"
        )  # v2 state machine head（v3 down_revision）

    return db_path, cfg, db_url, mock_settings


def test_v3_upgrade_adds_model_column_and_index(v2_db):
    """upgrade 到 v3 head：assets 表新增 model 列 + ix_assets_model 索引。"""
    db_path, cfg, db_url, mock_settings = v2_db
    engine = create_engine(db_url)

    # 前置断言：v2 状态下不存在 model 列
    cols_before = {c["name"] for c in inspect(engine).get_columns("assets")}
    assert "model" not in cols_before

    _clear_env_cache()
    with patch("asset_hub.config.Settings", return_value=mock_settings):
        command.upgrade(cfg, "head")

    # upgrade 后：列 + 索引存在
    engine = create_engine(db_url)
    cols = {c["name"] for c in inspect(engine).get_columns("assets")}
    assert "model" in cols

    indexes = {i["name"] for i in inspect(engine).get_indexes("assets")}
    assert "ix_assets_model" in indexes


def test_v3_downgrade_removes_model_column_and_index(v2_db):
    """upgrade 到 head 再 downgrade 回 v2：model 列 + ix_assets_model 索引一并消失。

    CL-1 加 v4 后 head 移到 v4，downgrade target 从 -1 → -2（v4 → v3 → v2）。
    """
    db_path, cfg, db_url, mock_settings = v2_db

    _clear_env_cache()
    with patch("asset_hub.config.Settings", return_value=mock_settings):
        command.upgrade(cfg, "head")

    _clear_env_cache()
    with patch("asset_hub.config.Settings", return_value=mock_settings):
        command.downgrade(cfg, "-2")

    engine = create_engine(db_url)
    cols = {c["name"] for c in inspect(engine).get_columns("assets")}
    assert "model" not in cols

    indexes = {i["name"] for i in inspect(engine).get_indexes("assets")}
    assert "ix_assets_model" not in indexes
