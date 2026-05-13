import pytest
from sqlmodel import Session

from asset_hub.services.asset_type import TypeService


@pytest.fixture()
def sample_type_nb(session: Session):
    return TypeService(session).create_type(
        name="笔记本电脑", code_prefix="NB", custom_fields=[]
    )


@pytest.fixture()
def sample_type_pj(session: Session):
    return TypeService(session).create_type(
        name="投影仪", code_prefix="PJ", custom_fields=[]
    )


@pytest.fixture()
def sample_asset(session: Session, sample_type_nb):
    from asset_hub.services.asset import AssetService
    svc = AssetService(session)
    return svc.register(
        name="X", type_id=sample_type_nb.id, custom_data={},
    )


@pytest.fixture()
def sample_asset_with_model(session: Session, sample_type_nb):
    from asset_hub.services.asset import AssetService
    svc = AssetService(session)
    return svc.register(
        name="X", type_id=sample_type_nb.id, custom_data={},
        model="原始型号-001",
    )
