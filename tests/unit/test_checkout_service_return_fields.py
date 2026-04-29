import pytest

from asset_hub.services.asset import AssetService
from asset_hub.services.asset_type import TypeService
from asset_hub.services.checkout import CheckoutService


@pytest.fixture
def asset_id(session):
    t = TypeService(session).create_type(name="B2-T", code_prefix="BT")
    a = AssetService(session).register(type_id=t.id, name="B2-A", custom_data={})
    CheckoutService(session).checkout(a.id, holder="张三", location="工位A")
    return a.id


def test_return_no_extra_fields_clears_location(session, asset_id):
    rec = CheckoutService(session).return_(asset_id, note="还了")
    assert rec.return_location is None
    assert rec.return_receiver is None
    a = AssetService(session).get_asset(asset_id)
    assert a.location is None


def test_return_with_location_sets_asset_location(session, asset_id):
    rec = CheckoutService(session).return_(
        asset_id, note="还", return_location="仓库A-3排"
    )
    assert rec.return_location == "仓库A-3排"
    a = AssetService(session).get_asset(asset_id)
    assert a.location == "仓库A-3排"


def test_return_with_receiver_only(session, asset_id):
    rec = CheckoutService(session).return_(
        asset_id, note=None, return_receiver="管理员甲"
    )
    assert rec.return_receiver == "管理员甲"
    assert rec.return_location is None
    a = AssetService(session).get_asset(asset_id)
    assert a.location is None  # location 留空时仍清空


def test_return_with_both(session, asset_id):
    rec = CheckoutService(session).return_(
        asset_id,
        note="测试",
        return_location="仓库B",
        return_receiver="管理员乙",
    )
    assert rec.return_location == "仓库B"
    assert rec.return_receiver == "管理员乙"
    a = AssetService(session).get_asset(asset_id)
    assert a.location == "仓库B"
    assert a.holder is None  # holder 仍清空（语义不变）
