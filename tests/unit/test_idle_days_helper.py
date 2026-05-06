"""idle_days 子查询 helper：取 Asset 上次进入 IDLE 的时间，
fallback 为 created_at（资产从未发生过 transition）。"""
from datetime import UTC, datetime, timedelta

import pytest
from sqlmodel import Session

from asset_hub.models.asset import Asset, AssetStatus
from asset_hub.models.asset_type import AssetType
from asset_hub.models.state_transition import StateTransitionRecord, TransitionKind
from asset_hub.services._idle_days import compute_idle_days_for_asset


@pytest.fixture
def session_with_idle_asset(session: Session):
    at = AssetType(name="Laptop", code_prefix="LT", custom_fields=[])
    session.add(at)
    session.flush()
    a = Asset(
        asset_code="L-001", name="MBP", type_id=at.id,
        status=AssetStatus.IDLE,
    )
    session.add(a)
    session.flush()
    return session, a


def test_idle_days_no_transitions_falls_back_to_created_at(session_with_idle_asset):
    """资产从未发生 transition → fallback Asset.created_at."""
    session, asset = session_with_idle_asset
    asset.created_at = datetime.now(UTC) - timedelta(days=42)
    session.flush()

    days = compute_idle_days_for_asset(session, asset.id)
    assert days == 42


def test_idle_days_uses_latest_idle_transition(session_with_idle_asset):
    """有多次进出 IDLE 的 transition → 取最近一次 to_status=IDLE 的 created_at."""
    session, asset = session_with_idle_asset
    # 历史：早 30 天进 IDLE → 20 天前出 IDLE → 5 天前回 IDLE
    session.add(StateTransitionRecord(
        asset_id=asset.id,
        kind=TransitionKind.RETURN,
        from_status=AssetStatus.IN_USE, to_status=AssetStatus.IDLE,
        created_at=datetime.now(UTC) - timedelta(days=30),
    ))
    session.add(StateTransitionRecord(
        asset_id=asset.id,
        kind=TransitionKind.CHECKOUT_INTERNAL,
        from_status=AssetStatus.IDLE, to_status=AssetStatus.IN_USE,
        created_at=datetime.now(UTC) - timedelta(days=20),
    ))
    session.add(StateTransitionRecord(
        asset_id=asset.id,
        kind=TransitionKind.RETURN,
        from_status=AssetStatus.IN_USE, to_status=AssetStatus.IDLE,
        created_at=datetime.now(UTC) - timedelta(days=5),
    ))
    session.flush()

    days = compute_idle_days_for_asset(session, asset.id)
    assert days == 5
