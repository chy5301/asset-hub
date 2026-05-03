import uuid
from datetime import UTC, datetime

import pytest
from sqlmodel import Session

from asset_hub.errors import IllegalTransitionError
from asset_hub.models.asset import Asset, AssetStatus
from asset_hub.models.asset_type import AssetType
from asset_hub.models.state_transition import TransitionKind
from asset_hub.services.transition import TransitionService


@pytest.fixture
def asset_type(session: Session) -> AssetType:
    t = AssetType(name="笔记本", code_prefix="NB", custom_fields=[])
    session.add(t)
    session.commit()
    session.refresh(t)
    return t


def _new_asset(
    session: Session,
    type_id: uuid.UUID,
    status=AssetStatus.IDLE,
    holder=None,
    location=None,
) -> Asset:
    a = Asset(
        asset_code="NB-001",
        name="测试机",
        type_id=type_id,
        status=status,
        holder=holder,
        location=location,
        custom_data={},
    )
    session.add(a)
    session.commit()
    session.refresh(a)
    return a


def test_checkout_internal_transitions_idle_to_in_use(session, asset_type):
    a = _new_asset(session, asset_type.id)
    svc = TransitionService(session)

    rec = svc.record_transition(
        asset_id=a.id,
        kind=TransitionKind.CHECKOUT_INTERNAL,
        to_holder="张三",
        to_location="1F-工位",
    )

    assert rec.kind == TransitionKind.CHECKOUT_INTERNAL
    assert rec.from_status == AssetStatus.IDLE
    assert rec.to_status == AssetStatus.IN_USE
    assert rec.to_holder == "张三"
    assert rec.to_location == "1F-工位"
    session.refresh(a)
    assert a.status == AssetStatus.IN_USE
    assert a.holder == "张三"
    assert a.location == "1F-工位"


def test_return_closes_open_checkout(session, asset_type):
    a = _new_asset(session, asset_type.id)
    svc = TransitionService(session)

    co = svc.record_transition(
        asset_id=a.id,
        kind=TransitionKind.CHECKOUT_INTERNAL,
        to_holder="张三",
    )
    ret = svc.record_transition(
        asset_id=a.id,
        kind=TransitionKind.RETURN,
        to_holder="仓管李四",
        to_location="仓库",
    )

    assert ret.closes_transition_id == co.id
    assert ret.from_status == AssetStatus.IN_USE
    assert ret.to_status == AssetStatus.IDLE
    session.refresh(a)
    assert a.status == AssetStatus.IDLE
    assert a.holder == "仓管李四"  # M3a: 跟随 to_holder，不再清空
    assert a.location == "仓库"


def test_return_with_null_to_holder_sets_asset_holder_null(session, asset_type):
    a = _new_asset(session, asset_type.id)
    svc = TransitionService(session)
    svc.record_transition(asset_id=a.id, kind=TransitionKind.CHECKOUT_INTERNAL, to_holder="X")
    svc.record_transition(asset_id=a.id, kind=TransitionKind.RETURN, to_holder=None)
    session.refresh(a)
    assert a.holder is None  # 无人值守仓库


def test_return_without_open_checkout_raises(session, asset_type):
    a = _new_asset(session, asset_type.id, status=AssetStatus.IN_USE, holder="X")
    svc = TransitionService(session)
    # IN_USE 但无对应 CHECKOUT_* transition 行
    with pytest.raises(IllegalTransitionError, match="未归还"):
        svc.record_transition(asset_id=a.id, kind=TransitionKind.RETURN, to_holder="Y")


def test_dispose_forces_null_holder_location(session, asset_type):
    a = _new_asset(session, asset_type.id, status=AssetStatus.RETIRED, holder="X", location="L")
    svc = TransitionService(session)
    rec = svc.record_transition(
        asset_id=a.id,
        kind=TransitionKind.DISPOSE,
        to_holder="尝试传值",  # 应被 forced_null 覆盖
        to_location="尝试传值",
    )
    assert rec.to_holder is None
    assert rec.to_location is None
    session.refresh(a)
    assert a.status == AssetStatus.DISPOSED
    assert a.holder is None
    assert a.location is None


def test_relocate_ignores_to_holder_keeps_current(session, asset_type):
    a = _new_asset(session, asset_type.id, status=AssetStatus.IN_USE, holder="原 holder")
    svc = TransitionService(session)
    rec = svc.record_transition(
        asset_id=a.id,
        kind=TransitionKind.RELOCATE,
        to_holder="尝试改",  # ignored
        to_location="新位置",
    )
    assert rec.to_holder == "原 holder"  # 保持现 holder
    assert rec.to_location == "新位置"
    session.refresh(a)
    assert a.holder == "原 holder"
    assert a.location == "新位置"
    assert a.status == AssetStatus.IN_USE  # status 不变


def test_relocate_missing_to_location_raises(session, asset_type):
    a = _new_asset(session, asset_type.id)
    svc = TransitionService(session)
    with pytest.raises(IllegalTransitionError, match="to_location"):
        svc.record_transition(asset_id=a.id, kind=TransitionKind.RELOCATE, to_location=None)


def test_transfer_holder_required_to_holder(session, asset_type):
    a = _new_asset(session, asset_type.id, holder="原")
    svc = TransitionService(session)
    with pytest.raises(IllegalTransitionError, match="to_holder"):
        svc.record_transition(asset_id=a.id, kind=TransitionKind.TRANSFER_HOLDER, to_holder=None)


def test_send_to_maintenance_optional_fields(session, asset_type):
    a = _new_asset(session, asset_type.id)
    svc = TransitionService(session)
    rec = svc.record_transition(asset_id=a.id, kind=TransitionKind.SEND_TO_MAINTENANCE)
    assert rec.to_status == AssetStatus.MAINTENANCE
    session.refresh(a)
    assert a.status == AssetStatus.MAINTENANCE


def test_retire_from_idle(session, asset_type):
    a = _new_asset(session, asset_type.id)
    svc = TransitionService(session)
    rec = svc.record_transition(asset_id=a.id, kind=TransitionKind.RETIRE)
    assert rec.to_status == AssetStatus.RETIRED


def test_retire_from_maintenance(session, asset_type):
    a = _new_asset(session, asset_type.id, status=AssetStatus.MAINTENANCE)
    svc = TransitionService(session)
    rec = svc.record_transition(asset_id=a.id, kind=TransitionKind.RETIRE)
    assert rec.to_status == AssetStatus.RETIRED


def test_dispose_from_idle_illegal(session, asset_type):
    a = _new_asset(session, asset_type.id)
    svc = TransitionService(session)
    with pytest.raises(IllegalTransitionError):
        svc.record_transition(asset_id=a.id, kind=TransitionKind.DISPOSE)


def test_disposed_asset_cannot_transition(session, asset_type):
    a = _new_asset(session, asset_type.id, status=AssetStatus.DISPOSED)
    svc = TransitionService(session)
    with pytest.raises(IllegalTransitionError):
        svc.record_transition(asset_id=a.id, kind=TransitionKind.RELOCATE, to_location="X")


def test_due_at_only_for_checkout(session, asset_type):
    a = _new_asset(session, asset_type.id)
    svc = TransitionService(session)
    due = datetime(2026, 12, 31, tzinfo=UTC)
    co = svc.record_transition(
        asset_id=a.id,
        kind=TransitionKind.CHECKOUT_INTERNAL,
        to_holder="X",
        due_at=due,
    )
    # SQLite 不存 tz，refresh 回来是 naive；只比较 UTC 时间分量
    assert co.due_at is not None
    assert co.due_at.replace(tzinfo=UTC) == due

    ret = svc.record_transition(
        asset_id=a.id,
        kind=TransitionKind.RETURN,
        due_at=due,  # 应被忽略
    )
    assert ret.due_at is None


def test_list_transitions_returns_desc_order(session, asset_type):
    a = _new_asset(session, asset_type.id)
    svc = TransitionService(session)
    svc.record_transition(asset_id=a.id, kind=TransitionKind.CHECKOUT_INTERNAL, to_holder="X")
    svc.record_transition(asset_id=a.id, kind=TransitionKind.RETURN)

    rows = svc.list_transitions(a.id)
    assert len(rows) == 2
    assert rows[0].kind == TransitionKind.RETURN  # 最新在前
    assert rows[1].kind == TransitionKind.CHECKOUT_INTERNAL


def test_recover_from_maintenance_returns_to_idle(session, asset_type):
    a = _new_asset(session, asset_type.id, status=AssetStatus.MAINTENANCE)
    rec = TransitionService(session).record_transition(
        asset_id=a.id, kind=TransitionKind.RECOVER_FROM_MAINTENANCE
    )
    assert rec.from_status == AssetStatus.MAINTENANCE
    assert rec.to_status == AssetStatus.IDLE
    session.refresh(a)
    assert a.status == AssetStatus.IDLE


def test_reinstate_from_retired_to_idle(session, asset_type):
    a = _new_asset(session, asset_type.id, status=AssetStatus.RETIRED)
    rec = TransitionService(session).record_transition(
        asset_id=a.id, kind=TransitionKind.REINSTATE
    )
    assert rec.from_status == AssetStatus.RETIRED
    assert rec.to_status == AssetStatus.IDLE
    session.refresh(a)
    assert a.status == AssetStatus.IDLE


def test_optional_location_null_preserves_current(session, asset_type):
    """spec §3.2: location_rule=optional 时，to_location=None 保留 asset.location（不清空）。"""
    a = _new_asset(session, asset_type.id, status=AssetStatus.IDLE, location="原位置")
    TransitionService(session).record_transition(
        asset_id=a.id, kind=TransitionKind.SEND_TO_MAINTENANCE, to_location=None
    )
    session.refresh(a)
    assert a.location == "原位置"
