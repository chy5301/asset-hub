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
