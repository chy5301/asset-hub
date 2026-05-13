"""v2 state machine migration 测：upgrade 改写 RELOCATE/TRANSFER_HOLDER → REASSIGN；downgrade 拒绝有 v2 数据。"""
import sys
import uuid
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text


def _make_cfg(db_path):
    """构建 alembic Config，指向指定 DB 路径。"""
    cfg = Config("alembic.ini")
    cfg.set_main_option("script_location", "src/asset_hub/alembic")
    cfg.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")
    return cfg


@pytest.fixture
def v1_db(tmp_path):
    """造一个 m3a baseline 的临时数据库（含 v1.0 transition kind 集合）。

    env.py 里 Settings() 会覆盖 sqlalchemy.url，所以 mock Settings 让它返回 tmp 路径。
    """
    db_path = tmp_path / "asset_hub.db"
    db_url = f"sqlite:///{db_path}"

    mock_settings = MagicMock()
    mock_settings.db_url = db_url

    cfg = _make_cfg(db_path)

    # env.py 每次被 alembic load 时都调用 Settings()；通过 patch 让其返回 tmp db_url
    # 同时强制清除已缓存的 env 模块，使 alembic 重新执行 env.py
    for key in list(sys.modules.keys()):
        if "asset_hub.alembic" in key or key.endswith(".env"):
            del sys.modules[key]

    with patch("asset_hub.config.Settings", return_value=mock_settings):
        command.upgrade(cfg, "c6c0960805a9")  # m3a baseline revision

    return db_path, cfg, db_url, mock_settings


def test_upgrade_relocate_to_reassign(v1_db):
    """upgrade 把 RELOCATE / TRANSFER_HOLDER 记录改写为 REASSIGN。"""
    db_path, cfg, db_url, mock_settings = v1_db
    engine = create_engine(db_url)
    asset_id = str(uuid.uuid4())
    type_id = str(uuid.uuid4())
    now = datetime.now(UTC).isoformat()

    # 插一条 v1.0 asset 和 RELOCATE/TRANSFER_HOLDER 记录
    with engine.begin() as conn:
        # asset_types 先建（FK 依赖）
        conn.execute(text(
            "INSERT INTO asset_types (id, name, code_prefix, custom_fields, created_at, updated_at) "
            "VALUES (:id, 'T', 'T', '[]', :now, :now)"
        ), {"id": type_id, "now": now})
        # asset 必填字段
        conn.execute(text(
            "INSERT INTO assets (id, asset_code, name, type_id, status, custom_data, created_at, updated_at) "
            "VALUES (:id, 'T-001', 'X', :tid, 'IDLE', '{}', :now, :now)"
        ), {"id": asset_id, "tid": type_id, "now": now})
        conn.execute(text(
            "INSERT INTO state_transition_records (id, asset_id, kind, from_status, to_status, created_at) "
            "VALUES (:tid, :aid, 'RELOCATE', 'IDLE', 'IDLE', :now)"
        ), {"tid": str(uuid.uuid4()), "aid": asset_id, "now": now})
        conn.execute(text(
            "INSERT INTO state_transition_records (id, asset_id, kind, from_status, to_status, created_at) "
            "VALUES (:tid, :aid, 'TRANSFER_HOLDER', 'IN_USE', 'IN_USE', :now)"
        ), {"tid": str(uuid.uuid4()), "aid": asset_id, "now": now})

    # upgrade 到 head
    for key in list(sys.modules.keys()):
        if "asset_hub.alembic" in key or key.endswith(".env"):
            del sys.modules[key]

    with patch("asset_hub.config.Settings", return_value=mock_settings):
        command.upgrade(cfg, "head")

    # 验证 RELOCATE / TRANSFER_HOLDER 全部变成 REASSIGN
    with engine.connect() as conn:
        rows = conn.execute(text("SELECT kind FROM state_transition_records")).all()
        assert len(rows) == 2
        assert all(r.kind == "REASSIGN" for r in rows)


def test_downgrade_rejects_v2_data(v1_db):
    """upgrade + 插 v2 BROKEN 数据 + downgrade 应抛错。"""
    db_path, cfg, db_url, mock_settings = v1_db
    engine = create_engine(db_url)

    for key in list(sys.modules.keys()):
        if "asset_hub.alembic" in key or key.endswith(".env"):
            del sys.modules[key]

    with patch("asset_hub.config.Settings", return_value=mock_settings):
        command.upgrade(cfg, "head")

    # 插一条 BROKEN 资产
    asset_id = str(uuid.uuid4())
    type_id = str(uuid.uuid4())
    now = datetime.now(UTC).isoformat()
    with engine.begin() as conn:
        conn.execute(text(
            "INSERT INTO asset_types (id, name, code_prefix, custom_fields, created_at, updated_at) "
            "VALUES (:id, 'T', 'T', '[]', :now, :now)"
        ), {"id": type_id, "now": now})
        conn.execute(text(
            "INSERT INTO assets (id, asset_code, name, type_id, status, custom_data, created_at, updated_at) "
            "VALUES (:id, 'T-002', 'Y', :tid, 'BROKEN', '{}', :now, :now)"
        ), {"id": asset_id, "tid": type_id, "now": now})

    for key in list(sys.modules.keys()):
        if "asset_hub.alembic" in key or key.endswith(".env"):
            del sys.modules[key]

    with pytest.raises(RuntimeError, match="BROKEN 状态资产"):
        with patch("asset_hub.config.Settings", return_value=mock_settings):
            command.downgrade(cfg, "-2")  # v3 → v2 → v1：触发 v2 downgrade guard（PR-3 加 v3 后 head 移到 v3）


def test_downgrade_rejects_v2_kind_transitions(v1_db):
    """upgrade + 插一条 REASSIGN transition record + downgrade 应抛错（第二个 guard）。"""
    db_path, cfg, db_url, mock_settings = v1_db
    engine = create_engine(db_url)

    for key in list(sys.modules.keys()):
        if "asset_hub.alembic" in key or key.endswith(".env"):
            del sys.modules[key]

    with patch("asset_hub.config.Settings", return_value=mock_settings):
        command.upgrade(cfg, "head")

    # 准备 type + asset（IDLE，不触发第一个 BROKEN guard）+ REASSIGN transition
    asset_id = str(uuid.uuid4())
    type_id = str(uuid.uuid4())
    now = datetime.now(UTC).isoformat()
    with engine.begin() as conn:
        conn.execute(text(
            "INSERT INTO asset_types (id, name, code_prefix, custom_fields, created_at, updated_at) "
            "VALUES (:id, 'T', 'T', '[]', :now, :now)"
        ), {"id": type_id, "now": now})
        conn.execute(text(
            "INSERT INTO assets (id, asset_code, name, type_id, status, custom_data, created_at, updated_at) "
            "VALUES (:id, 'T-003', 'Z', :tid, 'IDLE', '{}', :now, :now)"
        ), {"id": asset_id, "tid": type_id, "now": now})
        conn.execute(text(
            "INSERT INTO state_transition_records (id, asset_id, kind, from_status, to_status, created_at) "
            "VALUES (:tid, :aid, 'REASSIGN', 'IDLE', 'IDLE', :now)"
        ), {"tid": str(uuid.uuid4()), "aid": asset_id, "now": now})

    for key in list(sys.modules.keys()):
        if "asset_hub.alembic" in key or key.endswith(".env"):
            del sys.modules[key]

    with pytest.raises(RuntimeError, match="v2.0 新 kind 的 transition records"):
        with patch("asset_hub.config.Settings", return_value=mock_settings):
            command.downgrade(cfg, "-2")  # v3 → v2 → v1：触发 v2 downgrade guard（PR-3 加 v3 后 head 移到 v3）
