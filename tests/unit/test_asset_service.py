from datetime import date
from uuid import uuid4

import pytest
from sqlmodel import Session

from asset_hub.errors import DuplicateError, NotFoundError, ValidationError
from asset_hub.models.asset import AssetStatus
from asset_hub.services.asset import AssetService
from asset_hub.services.asset_type import TypeService


@pytest.fixture()
def type_svc(session: Session) -> TypeService:
    return TypeService(session)


@pytest.fixture()
def svc(session: Session) -> AssetService:
    return AssetService(session)


@pytest.fixture()
def laptop_type(type_svc: TypeService):
    return type_svc.create_type(
        name="笔记本电脑",
        code_prefix="NB",
        custom_fields=[
            {"key": "brand", "label": "品牌", "type": "string", "required": True},
            {"key": "os", "label": "操作系统", "type": "enum", "options": ["Windows", "macOS", "Linux"]},
            {"key": "ram_gb", "label": "内存(GB)", "type": "int"},
        ],
    )


@pytest.fixture()
def sample_type_nb(type_svc: TypeService):
    return type_svc.create_type(name="笔记本电脑", code_prefix="NB", custom_fields=[])


@pytest.fixture()
def sample_type_pj(type_svc: TypeService):
    return type_svc.create_type(name="投影仪", code_prefix="PJ", custom_fields=[])


class TestRegisterAsset:
    def test_register_minimal(self, svc: AssetService, laptop_type):
        a = svc.register(
            name="ThinkPad X1",
            type_id=laptop_type.id,
            custom_data={"brand": "Lenovo"},
        )
        assert a.id is not None
        assert a.name == "ThinkPad X1"
        assert a.status == AssetStatus.IDLE

    def test_register_with_all_fields(self, svc: AssetService, laptop_type):
        a = svc.register(
            name="MacBook Pro",
            type_id=laptop_type.id,
            serial_number="C02X12345",
            holder="张三",
            location="工位 5",
            notes="全新",
            custom_data={"brand": "Apple", "os": "macOS", "ram_gb": 16},
        )
        assert a.serial_number == "C02X12345"
        assert a.holder == "张三"
        assert a.custom_data["ram_gb"] == 16

    def test_register_nonexistent_type_raises(self, svc: AssetService):
        with pytest.raises(NotFoundError):
            svc.register(name="X", type_id=uuid4(), custom_data={})

    def test_register_duplicate_sn_raises(self, svc: AssetService, laptop_type):
        svc.register(name="A", type_id=laptop_type.id, serial_number="SN001", custom_data={"brand": "X"})
        with pytest.raises(DuplicateError):
            svc.register(name="B", type_id=laptop_type.id, serial_number="SN001", custom_data={"brand": "Y"})

    def test_register_missing_required_field_raises(self, svc: AssetService, laptop_type):
        with pytest.raises(ValidationError, match="品牌"):
            svc.register(name="X", type_id=laptop_type.id, custom_data={})

    def test_register_invalid_enum_raises(self, svc: AssetService, laptop_type):
        with pytest.raises(ValidationError, match="操作系统"):
            svc.register(
                name="X",
                type_id=laptop_type.id,
                custom_data={"brand": "Dell", "os": "FreeBSD"},
            )

    def test_register_unknown_custom_key_raises(self, svc: AssetService, laptop_type):
        with pytest.raises(ValidationError, match="unknown_key"):
            svc.register(
                name="X",
                type_id=laptop_type.id,
                custom_data={"brand": "Dell", "unknown_key": "val"},
            )


class TestListAssets:
    def test_list_empty(self, svc: AssetService):
        assert svc.list_assets() == []

    def test_list_all(self, svc: AssetService, laptop_type):
        svc.register(name="A", type_id=laptop_type.id, custom_data={"brand": "X"})
        svc.register(name="B", type_id=laptop_type.id, custom_data={"brand": "Y"})
        assert len(svc.list_assets()) == 2

    def test_filter_by_status(self, svc: AssetService, laptop_type):
        a = svc.register(name="A", type_id=laptop_type.id, custom_data={"brand": "X"})
        svc.register(name="B", type_id=laptop_type.id, custom_data={"brand": "Y"})
        svc.update_asset(a.id, status=AssetStatus.IN_USE)
        result = svc.list_assets(status=AssetStatus.IN_USE)
        assert len(result) == 1
        assert result[0].name == "A"

    def test_filter_by_q(self, svc: AssetService, laptop_type):
        svc.register(name="ThinkPad X1", type_id=laptop_type.id, custom_data={"brand": "Lenovo"})
        svc.register(name="MacBook Pro", type_id=laptop_type.id, custom_data={"brand": "Apple"})
        result = svc.list_assets(q="ThinkPad")
        assert len(result) == 1


class TestGetAsset:
    def test_get_existing(self, svc: AssetService, laptop_type):
        created = svc.register(name="X1", type_id=laptop_type.id, custom_data={"brand": "Lenovo"})
        fetched = svc.get_asset(created.id)
        assert fetched.name == "X1"

    def test_get_nonexistent_raises(self, svc: AssetService):
        with pytest.raises(NotFoundError):
            svc.get_asset(uuid4())


class TestUpdateAsset:
    def test_update_fields(self, svc: AssetService, laptop_type):
        a = svc.register(name="X1", type_id=laptop_type.id, custom_data={"brand": "Lenovo"})
        updated = svc.update_asset(a.id, holder="李四", location="机房 A")
        assert updated.holder == "李四"
        assert updated.location == "机房 A"

    def test_update_nonexistent_raises(self, svc: AssetService):
        with pytest.raises(NotFoundError):
            svc.update_asset(uuid4(), holder="X")


class TestDeleteAsset:
    def test_delete_existing(self, svc: AssetService, laptop_type):
        a = svc.register(name="X1", type_id=laptop_type.id, custom_data={"brand": "Lenovo"})
        svc.delete_asset(a.id)
        with pytest.raises(NotFoundError):
            svc.get_asset(a.id)

    def test_delete_nonexistent_raises(self, svc: AssetService):
        with pytest.raises(NotFoundError):
            svc.delete_asset(uuid4())


def test_register_auto_generates_asset_code(session, sample_type_nb):
    """同 type 多次 register，asset_code 按 prefix-001 / prefix-002 递增"""
    svc = AssetService(session)
    a1 = svc.register(name="X1", type_id=sample_type_nb.id, custom_data={})
    a2 = svc.register(name="X1 Carbon", type_id=sample_type_nb.id, custom_data={})
    a3 = svc.register(name="MacBook", type_id=sample_type_nb.id, custom_data={})
    assert a1.asset_code == "NB-001"
    assert a2.asset_code == "NB-002"
    assert a3.asset_code == "NB-003"


def test_register_per_type_seq_independent(session, sample_type_nb, sample_type_pj):
    """不同 type 的 seq 独立"""
    svc = AssetService(session)
    a_nb1 = svc.register(name="X1", type_id=sample_type_nb.id, custom_data={})
    a_pj1 = svc.register(name="投影仪", type_id=sample_type_pj.id, custom_data={})
    a_nb2 = svc.register(name="X1 Carbon", type_id=sample_type_nb.id, custom_data={})
    assert a_nb1.asset_code == "NB-001"
    assert a_pj1.asset_code == "PJ-001"
    assert a_nb2.asset_code == "NB-002"


def test_register_with_acquired_at(session, sample_type_nb):
    svc = AssetService(session)
    a = svc.register(
        name="X1",
        type_id=sample_type_nb.id,
        custom_data={},
        acquired_at=date(2025, 1, 15),
    )
    assert a.acquired_at == date(2025, 1, 15)


def test_register_acquired_at_optional(session, sample_type_nb):
    svc = AssetService(session)
    a = svc.register(name="X1", type_id=sample_type_nb.id, custom_data={})
    assert a.acquired_at is None


def test_asset_read_includes_type_name(session, sample_type_nb):
    from asset_hub.api.schemas.asset import AssetRead
    svc = AssetService(session)
    a = svc.register(name="X1", type_id=sample_type_nb.id, custom_data={})
    a_read = AssetRead.model_validate(a)
    assert a_read.type_name == "笔记本电脑"
    assert a_read.asset_code == "NB-001"


def test_list_assets_each_has_type_name(session, sample_type_nb, sample_type_pj):
    from asset_hub.api.schemas.asset import AssetRead
    svc = AssetService(session)
    svc.register(name="X1", type_id=sample_type_nb.id, custom_data={})
    svc.register(name="投影仪", type_id=sample_type_pj.id, custom_data={})

    assets = svc.list_assets()
    reads = [AssetRead.model_validate(a) for a in assets]
    type_names = {r.type_name for r in reads}
    assert type_names == {"笔记本电脑", "投影仪"}


def test_register_duplicate_serial_number_message(session, sample_type_nb):
    """SN 重复时错误消息应该是'序列号重复'，不该被误读为'asset_code 撞车'"""
    svc = AssetService(session)
    svc.register(name="X1", type_id=sample_type_nb.id, custom_data={}, serial_number="SN-DUP-001")
    with pytest.raises(DuplicateError, match="序列号"):
        svc.register(name="X2", type_id=sample_type_nb.id, custom_data={}, serial_number="SN-DUP-001")
