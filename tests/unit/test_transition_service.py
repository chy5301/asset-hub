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
    svc.record_transition(
        asset_id=a.id, kind=TransitionKind.CHECKOUT_INTERNAL, to_holder="X"
    )
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
    a = _new_asset(
        session, asset_type.id, status=AssetStatus.RETIRED, holder="X", location="L"
    )
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
    """DISPOSED 是终态，任何 transition 都应抛 IllegalTransitionError。"""
    a = _new_asset(session, asset_type.id, status=AssetStatus.DISPOSED)
    svc = TransitionService(session)
    with pytest.raises(IllegalTransitionError, match="不能从 DISPOSED 出发"):
        svc.record_transition(a.id, TransitionKind.REINSTATE)


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
    svc.record_transition(
        asset_id=a.id, kind=TransitionKind.CHECKOUT_INTERNAL, to_holder="X"
    )
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
    """v2.0 keep rule: SEND_TO_MAINTENANCE 不传 to_location（UNSET）→ 保留 asset.location。"""
    a = _new_asset(session, asset_type.id, status=AssetStatus.IDLE, location="原位置")
    TransitionService(session).record_transition(
        asset_id=a.id,
        kind=TransitionKind.SEND_TO_MAINTENANCE,
        # 不传 to_location → UNSET → keep
    )
    session.refresh(a)
    assert a.location == "原位置"


def test_send_to_maintenance_keep_holder_unset_retains_current(session, asset_type):
    """v2.0 keep rule + 不传 to_holder → 保留 asset.holder。"""
    a = _new_asset(session, asset_type.id, status=AssetStatus.IDLE, holder="张三")
    svc = TransitionService(session)

    rec = svc.record_transition(a.id, TransitionKind.SEND_TO_MAINTENANCE)

    session.refresh(a)
    assert a.holder == "张三"  # 保留
    assert a.status == AssetStatus.MAINTENANCE
    assert rec.to_holder == "张三"


def test_send_to_maintenance_keep_holder_explicit_none_clears(session, asset_type):
    """v2.0 keep rule + explicit to_holder=None → 清空。"""
    a = _new_asset(session, asset_type.id, status=AssetStatus.IDLE, holder="李四")
    svc = TransitionService(session)

    rec = svc.record_transition(
        a.id, TransitionKind.SEND_TO_MAINTENANCE, to_holder=None
    )

    session.refresh(a)
    assert a.holder is None  # 清空
    assert rec.to_holder is None


def test_send_to_maintenance_keep_holder_explicit_value_updates(session, asset_type):
    """v2.0 keep rule + explicit to_holder='X' → 改值。"""
    a = _new_asset(session, asset_type.id, status=AssetStatus.IDLE, holder="王五")
    svc = TransitionService(session)

    rec = svc.record_transition(
        a.id, TransitionKind.SEND_TO_MAINTENANCE, to_holder="维修方"
    )

    session.refresh(a)
    assert a.holder == "维修方"
    assert rec.to_holder == "维修方"


# ── Phase 2.4: 派出集 closes 通用化 ──────────────────────────────────────────


def test_closes_in_use_to_idle_via_return(session, asset_type):
    """IN_USE → IDLE(RETURN) 闭合 OPEN CHECKOUT（v1.0 行为保留）。"""
    a = _new_asset(session, asset_type.id, status=AssetStatus.IDLE)
    svc = TransitionService(session)
    checkout = svc.record_transition(
        a.id, TransitionKind.CHECKOUT_INTERNAL, to_holder="张三"
    )
    ret = svc.record_transition(a.id, TransitionKind.RETURN)
    assert ret.closes_transition_id == checkout.id


def test_no_closes_in_use_to_broken_via_report(session, asset_type):
    """IN_USE → BROKEN(REPORT_BROKEN) 不闭合 OPEN CHECKOUT（仍在派出集）。"""
    a = _new_asset(session, asset_type.id, status=AssetStatus.IDLE)
    svc = TransitionService(session)
    svc.record_transition(a.id, TransitionKind.CHECKOUT_INTERNAL, to_holder="李四")
    report = svc.record_transition(a.id, TransitionKind.REPORT_BROKEN)
    assert report.closes_transition_id is None  # 仍在派出集，不闭合


def test_closes_broken_to_idle_via_dismiss(session, asset_type):
    """BROKEN → IDLE(DISMISS) 闭合 OPEN CHECKOUT（走出派出集）。"""
    a = _new_asset(session, asset_type.id, status=AssetStatus.IDLE)
    svc = TransitionService(session)
    checkout = svc.record_transition(
        a.id, TransitionKind.CHECKOUT_INTERNAL, to_holder="王五"
    )
    svc.record_transition(
        a.id, TransitionKind.REPORT_BROKEN
    )  # IN_USE → BROKEN（不闭合）
    dismiss = svc.record_transition(
        a.id, TransitionKind.DISMISS
    )  # BROKEN → IDLE（闭合）
    assert dismiss.closes_transition_id == checkout.id


def test_closes_broken_to_maintenance(session, asset_type):
    """BROKEN → MAINTENANCE(SEND_TO_MAINTENANCE) 闭合 OPEN CHECKOUT。"""
    a = _new_asset(session, asset_type.id, status=AssetStatus.IDLE)
    svc = TransitionService(session)
    checkout = svc.record_transition(
        a.id, TransitionKind.CHECKOUT_INTERNAL, to_holder="A"
    )
    svc.record_transition(a.id, TransitionKind.REPORT_BROKEN)
    send = svc.record_transition(a.id, TransitionKind.SEND_TO_MAINTENANCE)
    assert send.closes_transition_id == checkout.id


def test_reassign_in_use_no_closes(session, asset_type):
    """IN_USE → IN_USE(REASSIGN) 不闭合（仍在派出集，self-loop）。"""
    a = _new_asset(session, asset_type.id, status=AssetStatus.IDLE)
    svc = TransitionService(session)
    svc.record_transition(a.id, TransitionKind.CHECKOUT_INTERNAL, to_holder="A")
    rea = svc.record_transition(a.id, TransitionKind.REASSIGN, to_holder="B")
    assert rea.closes_transition_id is None


def test_return_no_open_checkout_raises(session, asset_type):
    """RETURN 找不到 OPEN CHECKOUT 报错（v1.0 强约束保留）。"""
    # 直接 seed IN_USE 状态 + 无 checkout record
    a = _new_asset(session, asset_type.id, status=AssetStatus.IN_USE, holder="X")
    svc = TransitionService(session)
    with pytest.raises(IllegalTransitionError, match="未归还"):
        svc.record_transition(a.id, TransitionKind.RETURN)


def test_dismiss_no_open_checkout_ok(session, asset_type):
    """DISMISS 找不到 OPEN CHECKOUT 不报错（资产未派发就出现故障的边缘场景）。"""
    a = _new_asset(session, asset_type.id, status=AssetStatus.IDLE)
    svc = TransitionService(session)
    svc.record_transition(
        a.id, TransitionKind.REPORT_BROKEN
    )  # IDLE → BROKEN（IDLE 不在派出集，不闭合）
    dismiss = svc.record_transition(
        a.id, TransitionKind.DISMISS
    )  # BROKEN → IDLE（走出派出集）
    assert dismiss.closes_transition_id is None  # 没 OPEN 也合法


# ── Phase 2.5: REASSIGN 必改一项校验 ─────────────────────────────────────────


def test_reassign_no_change_raises(session, asset_type):
    """REASSIGN 不传任何字段 → 报错（必改一项）。"""
    a = _new_asset(
        session, asset_type.id, status=AssetStatus.IDLE, holder="X", location="L1"
    )
    svc = TransitionService(session)
    with pytest.raises(IllegalTransitionError, match="至少一项"):
        svc.record_transition(a.id, TransitionKind.REASSIGN)


def test_reassign_same_value_raises(session, asset_type):
    """REASSIGN 传当前值（无变化）→ 报错。"""
    a = _new_asset(
        session, asset_type.id, status=AssetStatus.IDLE, holder="X", location="L1"
    )
    svc = TransitionService(session)
    with pytest.raises(IllegalTransitionError, match="至少一项"):
        svc.record_transition(
            a.id, TransitionKind.REASSIGN, to_holder="X", to_location="L1"
        )


def test_reassign_changes_holder_only(session, asset_type):
    """REASSIGN --to-holder 改持有人，OK，location 保留（keep）。"""
    a = _new_asset(
        session, asset_type.id, status=AssetStatus.IDLE, holder="X", location="L1"
    )
    svc = TransitionService(session)
    rec = svc.record_transition(a.id, TransitionKind.REASSIGN, to_holder="Y")
    session.refresh(a)
    assert a.holder == "Y"
    assert a.location == "L1"  # 保留（UNSET → keep）
    assert rec.kind == TransitionKind.REASSIGN
    assert rec.from_holder == "X"
    assert rec.to_holder == "Y"
