from datetime import UTC, date, datetime, timedelta
from uuid import uuid4

import pytest
from sqlmodel import Session

from asset_hub.errors import DuplicateError, NotFoundError, ValidationError
from asset_hub.models.asset import Asset, AssetStatus
from asset_hub.models.asset_type import AssetType
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
    def test_update_notes(self, svc: AssetService, laptop_type):
        a = svc.register(name="X1", type_id=laptop_type.id, custom_data={"brand": "Lenovo"})
        updated = svc.update_asset(a.id, notes="新备注")
        assert updated.notes == "新备注"

    def test_update_nonexistent_raises(self, svc: AssetService):
        with pytest.raises(NotFoundError):
            svc.update_asset(uuid4(), notes="X")


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


def test_register_with_model(session, sample_type_nb):
    """register 时传 model，DB 应持久化。"""
    svc = AssetService(session)
    a = svc.register(
        name="开发本-01",
        type_id=sample_type_nb.id,
        custom_data={},
        model="ThinkPad X1 Carbon Gen 9",
    )
    session.refresh(a)
    assert a.model == "ThinkPad X1 Carbon Gen 9"


def test_register_without_model(session, sample_type_nb):
    """register 时不传 model，DB 应存 None。"""
    svc = AssetService(session)
    a = svc.register(name="X", type_id=sample_type_nb.id, custom_data={})
    session.refresh(a)
    assert a.model is None


def test_update_model_to_value(session, sample_asset):
    """update_asset 传 model='X' 设值。"""
    svc = AssetService(session)
    a = svc.update_asset(sample_asset.id, model="MacBook Pro 14")
    session.refresh(a)
    assert a.model == "MacBook Pro 14"


def test_update_model_to_null_explicit(session, sample_asset_with_model):
    """update_asset 传 model=None 显式清空。"""
    svc = AssetService(session)
    a = svc.update_asset(sample_asset_with_model.id, model=None)
    session.refresh(a)
    assert a.model is None


def test_update_model_unset_keeps_current(session, sample_asset_with_model):
    """update_asset 不传 model 参数，保持原值（UNSET 哨兵）。"""
    svc = AssetService(session)
    original_model = sample_asset_with_model.model
    a = svc.update_asset(sample_asset_with_model.id, name="新名")  # 不传 model
    session.refresh(a)
    assert a.model == original_model


def test_sort_by_model_accepted(session):
    """list_assets 接受 sort_by='model'，不报 ValidationError。"""
    svc = AssetService(session)
    result = svc.list_assets(sort_by="model", sort_order="asc")
    assert isinstance(result, list)


def test_sort_by_serial_number_accepted(session):
    """list_assets 接受 sort_by='serial_number'（v1 顺修）。"""
    svc = AssetService(session)
    result = svc.list_assets(sort_by="serial_number", sort_order="asc")
    assert isinstance(result, list)


def test_sort_by_unknown_rejected(session):
    """sort_by 用未知字段仍报 ValidationError（防回归）。"""
    svc = AssetService(session)
    with pytest.raises(ValidationError):
        svc.list_assets(sort_by="not_a_field")


def test_list_q_matches_model(session, sample_type_nb):
    """list_assets q 参数命中 model 字段。"""
    svc = AssetService(session)
    svc.register(
        name="A", type_id=sample_type_nb.id, custom_data={},
        model="ThinkPad X1 Carbon",
    )
    svc.register(
        name="B", type_id=sample_type_nb.id, custom_data={},
        model="MacBook Pro",
    )

    result = svc.list_assets(q="ThinkPad")
    assert len(result) == 1
    assert result[0].name == "A"


def test_register_duplicate_serial_number_message(session, sample_type_nb):
    """SN 重复时错误消息应该是'序列号重复'，不该被误读为'asset_code 撞车'"""
    svc = AssetService(session)
    svc.register(name="X1", type_id=sample_type_nb.id, custom_data={}, serial_number="SN-DUP-001")
    with pytest.raises(DuplicateError, match="序列号"):
        svc.register(name="X2", type_id=sample_type_nb.id, custom_data={}, serial_number="SN-DUP-001")


# ── sort / limit / offset tests ────────────────────────────────────────────────


def _create_idle_assets(session: Session, count: int) -> list[Asset]:
    """创建 N 个 IDLE 资产，错开 created_at（i=0 最早，i=N-1 最晚）."""
    at = AssetType(name="Laptop", code_prefix="SRT", custom_fields=[])
    session.add(at)
    session.flush()
    assets = []
    for i in range(count):
        a = Asset(asset_code=f"L-{i:03d}", name=f"L{i}", type_id=at.id, status=AssetStatus.IDLE)
        session.add(a)
        session.flush()
        # 让 created_at 错开
        a.created_at = datetime.now(UTC) - timedelta(days=count - i)
        assets.append(a)
    session.flush()
    return assets


def test_list_assets_sort_by_idle_days_desc(session: Session):
    """sort_by=idle_days, sort_order=desc → 最闲置的（早 created_at）排首位."""
    _create_idle_assets(session, 5)
    svc = AssetService(session)
    result = svc.list_assets(sort_by="idle_days", sort_order="desc")
    assert result[0].asset_code == "L-000"  # 最早创建 = 最闲置


def test_list_assets_limit_truncates(session: Session):
    _create_idle_assets(session, 10)
    svc = AssetService(session)
    result = svc.list_assets(limit=3)
    assert len(result) == 3


def test_list_assets_offset_skips(session: Session):
    _create_idle_assets(session, 5)
    svc = AssetService(session)
    full = svc.list_assets(sort_by="created_at", sort_order="asc")
    paged = svc.list_assets(sort_by="created_at", sort_order="asc", offset=2, limit=2)
    assert [a.id for a in paged] == [full[2].id, full[3].id]


def test_list_assets_unknown_sort_by_raises(session: Session):
    svc = AssetService(session)
    with pytest.raises(ValidationError, match="sort_by"):
        svc.list_assets(sort_by="invalid_field")


def test_list_assets_invalid_sort_order_raises(session: Session):
    svc = AssetService(session)
    with pytest.raises(ValidationError, match="sort_order"):
        svc.list_assets(sort_order="up")


def test_list_assets_negative_offset_raises(session: Session):
    svc = AssetService(session)
    with pytest.raises(ValidationError, match="offset"):
        svc.list_assets(offset=-1)


def test_list_assets_limit_over_max_raises(session: Session):
    svc = AssetService(session)
    with pytest.raises(ValidationError, match="limit"):
        svc.list_assets(limit=2000)


def test_list_assets_default_no_sort_no_limit(session: Session):
    """不传 sort/limit/offset → 行为与 main 当前一致（按 asset_code asc 全量）."""
    _create_idle_assets(session, 3)
    svc = AssetService(session)
    result = svc.list_assets()  # 全默认
    assert len(result) == 3
    # 项目默认排序是 asset_code.asc()——3 个 asset L-000/L-001/L-002 按字典序
    assert [a.asset_code for a in result] == ["L-000", "L-001", "L-002"]


def test_list_assets_sort_by_idle_days_asc(session: Session):
    """sort_by=idle_days, sort_order=asc → 最近 idle（晚 created_at）排首位."""
    _create_idle_assets(session, 5)
    svc = AssetService(session)
    result = svc.list_assets(sort_by="idle_days", sort_order="asc")
    assert result[0].asset_code == "L-004"  # 最晚创建 = 最少闲置 days


def test_list_assets_sort_by_acquired_at(session: Session):
    """sort_by=acquired_at 走 _SORT_COLUMN_MAP；NULL 处理由 SQLite 默认."""
    from datetime import date

    at = AssetType(name="L", code_prefix="ACQ", custom_fields=[])
    session.add(at)
    session.flush()
    a1 = Asset(asset_code="A-001", name="A1", type_id=at.id, status=AssetStatus.IDLE,
               acquired_at=date(2026, 1, 1))
    a2 = Asset(asset_code="A-002", name="A2", type_id=at.id, status=AssetStatus.IDLE,
               acquired_at=date(2026, 3, 1))
    a3 = Asset(asset_code="A-003", name="A3", type_id=at.id, status=AssetStatus.IDLE)  # NULL
    for a in [a1, a2, a3]:
        session.add(a)
    session.flush()

    svc = AssetService(session)
    desc_result = svc.list_assets(sort_by="acquired_at", sort_order="desc")
    # 仅断言非 NULL 的 a2 (2026-03-01) 排在 a1 (2026-01-01) 之前
    asset_codes_with_dates = [a.asset_code for a in desc_result if a.acquired_at is not None]
    assert asset_codes_with_dates == ["A-002", "A-001"]


def test_list_assets_limit_zero_raises(session: Session):
    svc = AssetService(session)
    with pytest.raises(ValidationError, match="limit"):
        svc.list_assets(limit=0)


def test_list_assets_limit_one_accepted(session: Session):
    _create_idle_assets(session, 3)
    svc = AssetService(session)
    result = svc.list_assets(limit=1)
    assert len(result) == 1


class TestListAssetsRetiredDisposedFilter:
    """5 态 filter 列表拼接 — M3e §3.2 薄弱点补测。"""

    def _seed_5_states(self, session: Session, type_id):
        """seed 5 个资产，每态各 1 个，返回插入的资产列表。"""
        from asset_hub.models.asset import Asset

        statuses = [
            (AssetStatus.IDLE, "F5-001"),
            (AssetStatus.IN_USE, "F5-002"),
            (AssetStatus.MAINTENANCE, "F5-003"),
            (AssetStatus.RETIRED, "F5-004"),
            (AssetStatus.DISPOSED, "F5-005"),
        ]
        assets = []
        for status, code in statuses:
            a = Asset(
                asset_code=code,
                name=f"资产-{code}",
                type_id=type_id,
                status=status,
                custom_data={},
            )
            session.add(a)
            assets.append(a)
        session.commit()
        return assets

    def test_default_excludes_retired_and_disposed(self, session: Session, sample_type_nb):
        self._seed_5_states(session, sample_type_nb.id)
        svc = AssetService(session)
        result = svc.list_assets()
        statuses = {a.status for a in result}
        assert AssetStatus.IDLE in statuses
        assert AssetStatus.IN_USE in statuses
        assert AssetStatus.MAINTENANCE in statuses
        assert AssetStatus.RETIRED not in statuses
        assert AssetStatus.DISPOSED not in statuses

    def test_include_retired_only(self, session: Session, sample_type_nb):
        self._seed_5_states(session, sample_type_nb.id)
        svc = AssetService(session)
        result = svc.list_assets(include_retired=True)
        statuses = {a.status for a in result}
        assert AssetStatus.RETIRED in statuses
        assert AssetStatus.DISPOSED not in statuses

    def test_include_disposed_only(self, session: Session, sample_type_nb):
        self._seed_5_states(session, sample_type_nb.id)
        svc = AssetService(session)
        result = svc.list_assets(include_disposed=True)
        statuses = {a.status for a in result}
        assert AssetStatus.DISPOSED in statuses
        assert AssetStatus.RETIRED not in statuses

    def test_include_both(self, session: Session, sample_type_nb):
        self._seed_5_states(session, sample_type_nb.id)
        svc = AssetService(session)
        result = svc.list_assets(include_retired=True, include_disposed=True)
        statuses = {a.status for a in result}
        assert statuses == {
            AssetStatus.IDLE,
            AssetStatus.IN_USE,
            AssetStatus.MAINTENANCE,
            AssetStatus.RETIRED,
            AssetStatus.DISPOSED,
        }

    def test_explicit_status_retired_overrides_default_exclusion(self, session: Session, sample_type_nb):
        """显式 status=RETIRED 时，即使 include_retired=False 也应返回 RETIRED 资产。"""
        self._seed_5_states(session, sample_type_nb.id)
        svc = AssetService(session)
        result = svc.list_assets(status=AssetStatus.RETIRED)
        statuses = {a.status for a in result}
        assert statuses == {AssetStatus.RETIRED}

    def test_explicit_status_disposed_overrides(self, session: Session, sample_type_nb):
        """显式 status=DISPOSED 时，即使 include_disposed=False 也应返回 DISPOSED 资产。"""
        self._seed_5_states(session, sample_type_nb.id)
        svc = AssetService(session)
        result = svc.list_assets(status=AssetStatus.DISPOSED)
        statuses = {a.status for a in result}
        assert statuses == {AssetStatus.DISPOSED}
