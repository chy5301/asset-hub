# tests/unit/test_transition_undo.py
import uuid
from datetime import UTC, datetime

import pytest
from sqlmodel import Session

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
