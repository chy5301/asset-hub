"""v4 migration 测：upgrade 加 brand 列 + ix_assets_brand 索引；数据回填；downgrade 回退干净。"""

import sys
import uuid
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text


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
def v3_db(tmp_path):
    """临时数据库，upgrade 到 v3 head（v4 之前，即 2d589d84e584）。

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
            cfg, "2d589d84e584"
        )  # v3 asset model column head（v4 down_revision）

    return db_path, cfg, db_url, mock_settings


def test_v4_upgrade_adds_brand_column_and_index(v3_db):
    """upgrade 到 v4 head：assets 表新增 brand 列 + ix_assets_brand 索引。"""
    db_path, cfg, db_url, mock_settings = v3_db
    engine = create_engine(db_url)

    # 前置断言：v3 状态下不存在 brand 列
    cols_before = {c["name"] for c in inspect(engine).get_columns("assets")}
    assert "brand" not in cols_before

    _clear_env_cache()
    with patch("asset_hub.config.Settings", return_value=mock_settings):
        command.upgrade(cfg, "head")

    # upgrade 后：列 + 索引存在
    engine = create_engine(db_url)
    cols = {c["name"] for c in inspect(engine).get_columns("assets")}
    assert "brand" in cols

    indexes = {i["name"] for i in inspect(engine).get_indexes("assets")}
    assert "ix_assets_brand" in indexes


def test_v4_data_migration_backfills_custom_data_brand(v3_db):
    """upgrade 到 v4 head：custom_data.brand 回填到顶层 brand 列；空串视同未填（→ null）。"""
    db_path, cfg, db_url, mock_settings = v3_db

    # 先在 v3 状态下插 3 行测试数据
    # v3 assets 表 NOT NULL 列：id / asset_code / name / type_id / status / custom_data / created_at / updated_at
    # type_id 是 FK，先插一个 asset_types 行
    type_id = str(uuid.uuid4())
    now = datetime.now(UTC).isoformat()

    engine = create_engine(db_url)
    with engine.begin() as conn:
        # 插 asset_types 行（NOT NULL：id / name / code_prefix / custom_fields / created_at / updated_at）
        conn.execute(
            text(
                "INSERT INTO asset_types (id, name, code_prefix, custom_fields, created_at, updated_at) "
                "VALUES (:id, :name, :prefix, :fields, :created_at, :updated_at)"
            ),
            {
                "id": type_id,
                "name": "Laptop",
                "prefix": "LP",
                "fields": "[]",
                "created_at": now,
                "updated_at": now,
            },
        )

        # row1: custom_data 含 brand = "Lenovo" → 回填后顶层 brand = "Lenovo"
        conn.execute(
            text(
                "INSERT INTO assets "
                "(id, asset_code, name, type_id, status, custom_data, created_at, updated_at) "
                "VALUES (:id, :asset_code, :name, :type_id, :status, :custom_data, :created_at, :updated_at)"
            ),
            {
                "id": str(uuid.uuid4()),
                "asset_code": "LP-001",
                "name": "ThinkPad X1",
                "type_id": type_id,
                "status": "IDLE",
                "custom_data": '{"brand": "Lenovo"}',
                "created_at": now,
                "updated_at": now,
            },
        )

        # row2: custom_data 不含 brand → 回填后顶层 brand = null
        conn.execute(
            text(
                "INSERT INTO assets "
                "(id, asset_code, name, type_id, status, custom_data, created_at, updated_at) "
                "VALUES (:id, :asset_code, :name, :type_id, :status, :custom_data, :created_at, :updated_at)"
            ),
            {
                "id": str(uuid.uuid4()),
                "asset_code": "LP-002",
                "name": "MacBook Pro",
                "type_id": type_id,
                "status": "IDLE",
                "custom_data": "{}",
                "created_at": now,
                "updated_at": now,
            },
        )

        # row3: custom_data 含 brand = ""（空字符串）→ 回填后顶层 brand = null（空串视同未填）
        conn.execute(
            text(
                "INSERT INTO assets "
                "(id, asset_code, name, type_id, status, custom_data, created_at, updated_at) "
                "VALUES (:id, :asset_code, :name, :type_id, :status, :custom_data, :created_at, :updated_at)"
            ),
            {
                "id": str(uuid.uuid4()),
                "asset_code": "LP-003",
                "name": "Dell XPS",
                "type_id": type_id,
                "status": "IDLE",
                "custom_data": '{"brand": ""}',
                "created_at": now,
                "updated_at": now,
            },
        )

    # 跑 v4 upgrade
    _clear_env_cache()
    with patch("asset_hub.config.Settings", return_value=mock_settings):
        command.upgrade(cfg, "head")

    # 断言回填结果
    engine = create_engine(db_url)
    with engine.connect() as conn:
        rows = conn.execute(
            text("SELECT asset_code, brand FROM assets ORDER BY asset_code")
        ).fetchall()

    assert rows == [("LP-001", "Lenovo"), ("LP-002", None), ("LP-003", None)]


def test_v4_downgrade_drops_brand_column(v3_db):
    """upgrade 到 v4 head 再 downgrade -1：brand 列 + ix_assets_brand 索引一并消失。"""
    db_path, cfg, db_url, mock_settings = v3_db

    _clear_env_cache()
    with patch("asset_hub.config.Settings", return_value=mock_settings):
        command.upgrade(cfg, "head")

    # 前置断言：upgrade 到 v4 head 后 brand 列必须存在，才能验证 downgrade 能正确删除它
    engine = create_engine(db_url)
    cols_after_upgrade = {c["name"] for c in inspect(engine).get_columns("assets")}
    assert "brand" in cols_after_upgrade, (
        "v4 migration 尚未实现：upgrade head 后 brand 列不存在"
    )

    _clear_env_cache()
    with patch("asset_hub.config.Settings", return_value=mock_settings):
        command.downgrade(cfg, "-1")

    engine = create_engine(db_url)
    cols = {c["name"] for c in inspect(engine).get_columns("assets")}
    assert "brand" not in cols

    indexes = {i["name"] for i in inspect(engine).get_indexes("assets")}
    assert "ix_assets_brand" not in indexes
