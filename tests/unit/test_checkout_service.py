from uuid import uuid4

import pytest
from sqlmodel import Session

from asset_hub.errors import NotFoundError, StateError
from asset_hub.models.asset import AssetStatus
from asset_hub.services.asset import AssetService
from asset_hub.services.asset_type import TypeService
from asset_hub.services.checkout import CheckoutService


@pytest.fixture()
def type_svc(session: Session) -> TypeService:
    return TypeService(session)


@pytest.fixture()
def asset_svc(session: Session) -> AssetService:
    return AssetService(session)


@pytest.fixture()
def checkout_svc(session: Session) -> CheckoutService:
    return CheckoutService(session)


@pytest.fixture()
def simple_type(type_svc: TypeService):
    return type_svc.create_type(name="笔记本", code_prefix="NB", custom_fields=[])


@pytest.fixture()
def idle_asset(asset_svc: AssetService, simple_type):
    return asset_svc.register(name="X1", type_id=simple_type.id, custom_data={})


class TestCheckout:
    def test_checkout_idle_asset(
        self,
        checkout_svc: CheckoutService,
        asset_svc: AssetService,
        idle_asset,
    ):
        rec = checkout_svc.checkout(
            asset_id=idle_asset.id,
            holder="张三",
            location="工位 5",
            note="借用一周",
        )

        assert rec.asset_id == idle_asset.id
        assert rec.holder == "张三"
        assert rec.location == "工位 5"
        assert rec.checkout_note == "借用一周"
        assert rec.returned_at is None

        updated = asset_svc.get_asset(idle_asset.id)
        assert updated.status == AssetStatus.IN_USE
        assert updated.holder == "张三"
        assert updated.location == "工位 5"

    def test_checkout_nonexistent_raises(self, checkout_svc: CheckoutService):
        with pytest.raises(NotFoundError):
            checkout_svc.checkout(asset_id=uuid4(), holder="张三")

    def test_checkout_already_in_use_raises(
        self,
        checkout_svc: CheckoutService,
        idle_asset,
    ):
        checkout_svc.checkout(asset_id=idle_asset.id, holder="张三")
        with pytest.raises(StateError, match="已派发"):
            checkout_svc.checkout(asset_id=idle_asset.id, holder="李四")

    def test_checkout_retired_raises(
        self,
        checkout_svc: CheckoutService,
        asset_svc: AssetService,
        idle_asset,
    ):
        asset_svc.update_asset(idle_asset.id, status=AssetStatus.RETIRED)
        with pytest.raises(StateError, match="RETIRED"):
            checkout_svc.checkout(asset_id=idle_asset.id, holder="张三")

    def test_checkout_maintenance_raises(
        self,
        checkout_svc: CheckoutService,
        asset_svc: AssetService,
        idle_asset,
    ):
        asset_svc.update_asset(idle_asset.id, status=AssetStatus.MAINTENANCE)
        with pytest.raises(StateError, match="MAINTENANCE"):
            checkout_svc.checkout(asset_id=idle_asset.id, holder="张三")

    def test_checkout_location_optional(
        self,
        checkout_svc: CheckoutService,
        idle_asset,
    ):
        rec = checkout_svc.checkout(asset_id=idle_asset.id, holder="张三")
        assert rec.location is None
        assert rec.checkout_note is None


class TestReturn:
    def test_return_closes_record(
        self,
        checkout_svc: CheckoutService,
        asset_svc: AssetService,
        idle_asset,
    ):
        checkout_svc.checkout(
            asset_id=idle_asset.id, holder="张三", location="工位 5"
        )
        rec = checkout_svc.return_(asset_id=idle_asset.id, note="完好")

        assert rec.returned_at is not None
        assert rec.return_note == "完好"

        updated = asset_svc.get_asset(idle_asset.id)
        assert updated.status == AssetStatus.IDLE
        assert updated.holder is None
        assert updated.location is None

    def test_return_without_open_checkout_raises(
        self,
        checkout_svc: CheckoutService,
        idle_asset,
    ):
        with pytest.raises(StateError, match="无未归还"):
            checkout_svc.return_(asset_id=idle_asset.id)

    def test_return_nonexistent_raises(self, checkout_svc: CheckoutService):
        with pytest.raises(NotFoundError):
            checkout_svc.return_(asset_id=uuid4())

    def test_return_allows_recheckout(
        self,
        checkout_svc: CheckoutService,
        idle_asset,
    ):
        checkout_svc.checkout(asset_id=idle_asset.id, holder="张三")
        checkout_svc.return_(asset_id=idle_asset.id)
        rec = checkout_svc.checkout(asset_id=idle_asset.id, holder="李四")
        assert rec.holder == "李四"


class TestHistory:
    def test_history_empty(
        self,
        checkout_svc: CheckoutService,
        idle_asset,
    ):
        assert checkout_svc.history(asset_id=idle_asset.id) == []

    def test_history_lists_all_records_newest_first(
        self,
        checkout_svc: CheckoutService,
        idle_asset,
    ):
        first = checkout_svc.checkout(asset_id=idle_asset.id, holder="张三")
        checkout_svc.return_(asset_id=idle_asset.id)
        second = checkout_svc.checkout(asset_id=idle_asset.id, holder="李四")

        records = checkout_svc.history(asset_id=idle_asset.id)

        assert [r.id for r in records] == [second.id, first.id]
        assert records[0].returned_at is None
        assert records[1].returned_at is not None

    def test_history_nonexistent_asset_raises(
        self, checkout_svc: CheckoutService
    ):
        with pytest.raises(NotFoundError):
            checkout_svc.history(asset_id=uuid4())
