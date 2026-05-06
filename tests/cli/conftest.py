import pytest

import asset_hub.db as db_mod


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    monkeypatch.setenv("ASSET_HUB_DATA_DIR", str(tmp_path))
    db_mod.reset_engine()
    yield tmp_path
    db_mod.reset_engine()


@pytest.fixture
def isolated_db_with_idle_assets(isolated_db):
    """创建 5 个 IDLE 资产用于 list/sort 测试."""
    from asset_hub.cli.deps import cli_session
    from asset_hub.models.asset import Asset, AssetStatus
    from asset_hub.services.asset_type import TypeService

    with cli_session() as session:
        type_svc = TypeService(session)
        at = type_svc.create_type(name="LaptopCli", code_prefix="LCL", custom_fields=[])
        for i in range(5):
            session.add(Asset(
                asset_code=f"LCL-{i:03d}",
                name=f"LaptopCli-{i}",
                type_id=at.id,
                status=AssetStatus.IDLE,
            ))
        session.commit()
    return None


@pytest.fixture
def populated_cli_db(isolated_db):
    """CLI stats 测试 fixture：创若干资产 (3 IDLE / 1 IN_USE / 1 RETIRED).

    无 transition record——idle_top 排序由 created_at fallback 覆盖；
    Task 8 unit 测试已覆盖含 transition 场景。"""
    from asset_hub.cli.deps import cli_session
    from asset_hub.models.asset import Asset, AssetStatus
    from asset_hub.services.asset_type import TypeService

    with cli_session() as session:
        ts = TypeService(session)
        at = ts.create_type(name="LaptopForStats", code_prefix="LFS", custom_fields=[])
        # 5 资产：3 IDLE / 1 IN_USE / 1 RETIRED
        for i in range(3):
            session.add(Asset(
                asset_code=f"LFS-{i:03d}",
                name=f"L{i}",
                type_id=at.id,
                status=AssetStatus.IDLE,
            ))
        session.add(Asset(
            asset_code="LFS-INU",
            name="U1",
            type_id=at.id,
            status=AssetStatus.IN_USE,
            holder="李四",
        ))
        session.add(Asset(
            asset_code="LFS-RET",
            name="R1",
            type_id=at.id,
            status=AssetStatus.RETIRED,
            holder="王五",
        ))
        session.commit()
    return None
