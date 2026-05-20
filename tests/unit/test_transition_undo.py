# tests/unit/test_transition_undo.py
import uuid
from datetime import UTC, datetime

import pytest
from sqlmodel import Session

from asset_hub.models.asset import Asset, AssetStatus
from asset_hub.models.asset_type import AssetType
from asset_hub.models.state_transition import StateTransitionRecord, TransitionKind
from asset_hub.repositories.state_transition import TransitionRepository


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
