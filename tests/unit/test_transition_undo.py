# tests/unit/test_transition_undo.py
import uuid
from datetime import UTC, datetime

import pytest
from sqlmodel import Session

from asset_hub.errors import NotFoundError, StateError
from asset_hub.models.asset import Asset, AssetStatus
from asset_hub.models.asset_type import AssetType
from asset_hub.models.state_transition import StateTransitionRecord, TransitionKind
from asset_hub.repositories.state_transition import TransitionRepository
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
    *,
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


# ===== Repository 层 =====


def test_repo_find_last_returns_none_when_no_records(session, asset_type):
    a = _new_asset(session, asset_type.id)
    repo = TransitionRepository(session)
    assert repo.find_last(a.id) is None


def test_repo_find_last_returns_newest_by_created_at(session, asset_type):
    a = _new_asset(session, asset_type.id)
    repo = TransitionRepository(session)
    older = StateTransitionRecord(
        asset_id=a.id,
        kind=TransitionKind.REASSIGN,
        from_status=AssetStatus.IDLE,
        to_status=AssetStatus.IDLE,
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    newer = StateTransitionRecord(
        asset_id=a.id,
        kind=TransitionKind.REASSIGN,
        from_status=AssetStatus.IDLE,
        to_status=AssetStatus.IDLE,
        created_at=datetime(2026, 5, 20, tzinfo=UTC),
    )
    session.add(older)
    session.add(newer)
    session.commit()

    last = repo.find_last(a.id)
    assert last is not None
    assert last.id == newer.id


def test_repo_delete_removes_row(session, asset_type):
    a = _new_asset(session, asset_type.id)
    repo = TransitionRepository(session)
    rec = StateTransitionRecord(
        asset_id=a.id,
        kind=TransitionKind.REASSIGN,
        from_status=AssetStatus.IDLE,
        to_status=AssetStatus.IDLE,
    )
    session.add(rec)
    session.commit()
    session.refresh(rec)

    repo.delete(rec)
    session.commit()
    assert repo.find_last(a.id) is None


# ===== Service 层 happy path =====


def test_undo_checkout_restores_idle(session, asset_type):
    a = _new_asset(session, asset_type.id)
    svc = TransitionService(session)
    svc.record_transition(
        asset_id=a.id,
        kind=TransitionKind.CHECKOUT_INTERNAL,
        to_holder="张三",
        to_location="1F-工位",
    )

    snapshot = svc.undo_last_transition(a.id)

    session.refresh(a)
    assert a.status == AssetStatus.IDLE
    assert a.holder is None
    assert a.location is None
    assert snapshot.kind == TransitionKind.CHECKOUT_INTERNAL
    assert snapshot.to_holder == "张三"
    assert TransitionRepository(session).find_last(a.id) is None


def test_undo_return_reopens_original_checkout(session, asset_type):
    a = _new_asset(session, asset_type.id)
    svc = TransitionService(session)
    co = svc.record_transition(
        asset_id=a.id,
        kind=TransitionKind.CHECKOUT_INTERNAL,
        to_holder="张三",
    )
    svc.record_transition(asset_id=a.id, kind=TransitionKind.RETURN)

    svc.undo_last_transition(a.id)

    session.refresh(a)
    assert a.status == AssetStatus.IN_USE
    assert a.holder == "张三"
    repo = TransitionRepository(session)
    last = repo.find_last(a.id)
    assert last is not None and last.id == co.id
    # 原 CHECKOUT 应重新被认作 OPEN
    assert repo.find_open_checkout_id(a.id) == co.id


def test_undo_dispose_restores_retired(session, asset_type):
    """验证 Q1=B：DISPOSE 是元命令可撤销，绕过状态机终态约束。"""
    a = _new_asset(session, asset_type.id, status=AssetStatus.RETIRED)
    svc = TransitionService(session)
    svc.record_transition(asset_id=a.id, kind=TransitionKind.DISPOSE)
    assert a.status == AssetStatus.DISPOSED  # sanity

    svc.undo_last_transition(a.id)

    session.refresh(a)
    assert a.status == AssetStatus.RETIRED
    assert TransitionRepository(session).find_last(a.id) is None


def test_undo_reassign_restores_holder_and_location(session, asset_type):
    a = _new_asset(session, asset_type.id, holder="原持有", location="原位置")
    svc = TransitionService(session)
    svc.record_transition(
        asset_id=a.id,
        kind=TransitionKind.REASSIGN,
        to_holder="新持有",
        to_location="新位置",
    )

    svc.undo_last_transition(a.id)

    session.refresh(a)
    assert a.holder == "原持有"
    assert a.location == "原位置"
    assert a.status == AssetStatus.IDLE


# ===== Service 层错误 / 余下场景 =====


def test_undo_without_any_transition_raises_state_conflict(session, asset_type):
    a = _new_asset(session, asset_type.id)
    svc = TransitionService(session)
    with pytest.raises(StateError) as exc_info:
        svc.undo_last_transition(a.id)
    assert "无可撤销的流转记录" in exc_info.value.message
    assert exc_info.value.hint is not None
    assert "asset delete" in exc_info.value.hint
    assert exc_info.value.affected_resource_id == str(a.id)


def test_undo_nonexistent_asset_raises_not_found(session):
    svc = TransitionService(session)
    bogus = uuid.uuid4()
    with pytest.raises(NotFoundError):
        svc.undo_last_transition(bogus)


def test_undo_twice_second_raises_state_conflict(session, asset_type):
    a = _new_asset(session, asset_type.id)
    svc = TransitionService(session)
    svc.record_transition(
        asset_id=a.id, kind=TransitionKind.CHECKOUT_INTERNAL, to_holder="张三"
    )
    svc.undo_last_transition(a.id)

    with pytest.raises(StateError):
        svc.undo_last_transition(a.id)


def test_undo_checkout_with_due_at_no_residue(session, asset_type):
    """due_at 仅在 transition 行上，asset 表无该字段，undo 后无残留。"""
    a = _new_asset(session, asset_type.id)
    svc = TransitionService(session)
    svc.record_transition(
        asset_id=a.id,
        kind=TransitionKind.CHECKOUT_INTERNAL,
        to_holder="张三",
        due_at=datetime(2026, 12, 1, tzinfo=UTC),
    )
    svc.undo_last_transition(a.id)
    session.refresh(a)
    assert a.status == AssetStatus.IDLE
    assert TransitionRepository(session).find_last(a.id) is None


def test_undo_recover_after_send_to_maintenance_keeps_holder_location(
    session, asset_type
):
    """register → send-to-maintenance → recover → undo
    asset 回 MAINTENANCE，holder/location 由 keep 规则保留 register 时的值。
    """
    a = _new_asset(session, asset_type.id, holder="李仓管", location="备件柜")
    svc = TransitionService(session)
    svc.record_transition(asset_id=a.id, kind=TransitionKind.SEND_TO_MAINTENANCE)
    svc.record_transition(asset_id=a.id, kind=TransitionKind.RECOVER_FROM_MAINTENANCE)

    svc.undo_last_transition(a.id)

    session.refresh(a)
    assert a.status == AssetStatus.MAINTENANCE
    assert a.holder == "李仓管"
    assert a.location == "备件柜"


def test_undo_chain_walks_back_to_register_state(session, asset_type):
    """连续多步 undo：checkout → return → undo(return) → undo(checkout)
    第一次 undo 删 RETURN，asset 回 IN_USE 且原 CHECKOUT 重开 OPEN；
    第二次 undo 删 CHECKOUT，asset 回 IDLE 且 transition 表为空。
    与 test_undo_twice_second_raises_state_conflict 不同：那条测的是
    只有 1 条 transition 时连续 undo 2 次第二次报错；这条测的是有 2 条
    transition 时连续 undo 2 次全部成功。
    """
    a = _new_asset(session, asset_type.id)
    svc = TransitionService(session)
    repo = TransitionRepository(session)
    co = svc.record_transition(
        asset_id=a.id, kind=TransitionKind.CHECKOUT_INTERNAL, to_holder="张三"
    )
    svc.record_transition(asset_id=a.id, kind=TransitionKind.RETURN)

    svc.undo_last_transition(a.id)  # 删 RETURN
    session.refresh(a)
    assert a.status == AssetStatus.IN_USE
    assert repo.find_open_checkout_id(a.id) == co.id

    svc.undo_last_transition(a.id)  # 删 CHECKOUT
    session.refresh(a)
    assert a.status == AssetStatus.IDLE
    assert a.holder is None
    assert repo.find_last(a.id) is None


def test_undo_report_broken_restores_in_use_keeps_checkout_open(session, asset_type):
    """REPORT_BROKEN (IN_USE → BROKEN) 不闭合 OPEN CHECKOUT
    （IN_USE 和 BROKEN 都属 PERSISTED_CHECKOUT_STATES，不触发 closes 逻辑）。
    undo 后 asset 回 IN_USE，原 CHECKOUT 仍 OPEN（它从来就没被闭合）。
    """
    a = _new_asset(session, asset_type.id)
    svc = TransitionService(session)
    repo = TransitionRepository(session)
    co = svc.record_transition(
        asset_id=a.id, kind=TransitionKind.CHECKOUT_INTERNAL, to_holder="张三"
    )
    rb = svc.record_transition(asset_id=a.id, kind=TransitionKind.REPORT_BROKEN)
    assert rb.closes_transition_id is None  # 不闭合 CHECKOUT
    assert repo.find_open_checkout_id(a.id) == co.id  # CHECKOUT 仍 OPEN

    svc.undo_last_transition(a.id)

    session.refresh(a)
    assert a.status == AssetStatus.IN_USE
    assert a.holder == "张三"
    assert repo.find_open_checkout_id(a.id) == co.id  # 仍 OPEN


def test_undo_declare_unrepairable_restores_maintenance(session, asset_type):
    """DECLARE_UNREPAIRABLE (MAINTENANCE → BROKEN) undo 后回 MAINTENANCE，
    holder/location 由 keep rule 保留 register 时的值。
    """
    a = _new_asset(session, asset_type.id, holder="维修工", location="维修间")
    svc = TransitionService(session)
    svc.record_transition(asset_id=a.id, kind=TransitionKind.SEND_TO_MAINTENANCE)
    svc.record_transition(asset_id=a.id, kind=TransitionKind.DECLARE_UNREPAIRABLE)
    session.refresh(a)
    assert a.status == AssetStatus.BROKEN  # sanity

    svc.undo_last_transition(a.id)

    session.refresh(a)
    assert a.status == AssetStatus.MAINTENANCE
    assert a.holder == "维修工"
    assert a.location == "维修间"
