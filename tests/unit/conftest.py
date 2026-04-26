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
