import pytest

from asset_hub.errors import ConflictError, NotFoundError
from asset_hub.services.asset import AssetService
from asset_hub.services.asset_type import TypeService


def test_delete_type_no_assets_succeeds(session):
    svc = TypeService(session)
    t = svc.create_type(name="测试-删除", code_prefix="DT")
    svc.delete_type(t.id)
    with pytest.raises(NotFoundError):
        svc.get_type(t.id)


def test_delete_type_with_assets_raises_conflict(session):
    type_svc = TypeService(session)
    t = type_svc.create_type(name="测试-冲突", code_prefix="CF")
    asset_svc = AssetService(session)
    asset_svc.register(type_id=t.id, name="资产1", custom_data={})

    with pytest.raises(ConflictError, match="1"):
        type_svc.delete_type(t.id)


def test_delete_type_not_found_raises(session):
    import uuid

    svc = TypeService(session)
    with pytest.raises(NotFoundError):
        svc.delete_type(uuid.uuid4())
