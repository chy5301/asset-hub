from datetime import UTC, datetime, timedelta

import pytest
from sqlmodel import Session

from asset_hub.errors import ValidationError
from asset_hub.models.asset import Asset, AssetStatus
from asset_hub.models.asset_type import AssetType
from asset_hub.models.state_transition import StateTransitionRecord, TransitionKind
from asset_hub.services.stats import StatsService


@pytest.fixture
def populated_session(session: Session):
    """5 资产：3 IDLE / 1 IN_USE / 1 RETIRED；2 type；2 holder."""
    laptop = AssetType(name="Laptop", code_prefix="LP", custom_fields=[])
    gpu = AssetType(name="GPU", code_prefix="GP", custom_fields=[])
    session.add(laptop)
    session.add(gpu)
    session.flush()

    a1 = Asset(
        asset_code="L-001",
        name="L1",
        type_id=laptop.id,
        status=AssetStatus.IDLE,
        holder=None,
    )
    a2 = Asset(
        asset_code="L-002",
        name="L2",
        type_id=laptop.id,
        status=AssetStatus.IDLE,
        holder="张三",
    )
    a3 = Asset(asset_code="G-001", name="G1", type_id=gpu.id, status=AssetStatus.IDLE)
    a4 = Asset(
        asset_code="L-003",
        name="L3",
        type_id=laptop.id,
        status=AssetStatus.IN_USE,
        holder="李四",
    )
    a5 = Asset(
        asset_code="G-002",
        name="G2",
        type_id=gpu.id,
        status=AssetStatus.RETIRED,
        holder="王五",
    )
    for a in [a1, a2, a3, a4, a5]:
        session.add(a)
    session.flush()

    # a1 30 天前进 IDLE，a2 5 天前进 IDLE，a3 created_at = 50 天前（fallback）
    session.add(
        StateTransitionRecord(
            asset_id=a1.id,
            kind=TransitionKind.RETURN,
            from_status=AssetStatus.IN_USE,
            to_status=AssetStatus.IDLE,
            created_at=datetime.now(UTC) - timedelta(days=30),
        )
    )
    session.add(
        StateTransitionRecord(
            asset_id=a2.id,
            kind=TransitionKind.RETURN,
            from_status=AssetStatus.IN_USE,
            to_status=AssetStatus.IDLE,
            created_at=datetime.now(UTC) - timedelta(days=5),
        )
    )
    a3.created_at = datetime.now(UTC) - timedelta(days=50)
    session.flush()

    return session


def test_get_dashboard_stats_default_excludes_retired_disposed(populated_session):
    svc = StatsService(populated_session)
    stats = svc.get_dashboard_stats()
    assert "RETIRED" not in stats.status_distribution
    assert stats.status_distribution.get("IDLE") == 3
    assert stats.status_distribution.get("IN_USE") == 1
    assert stats.summary.include_retired is False
    assert stats.summary.total_assets == 5
    assert stats.summary.registered_assets == 4


def test_get_dashboard_stats_include_retired(populated_session):
    """include_retired=True 让 status_distribution 含 RETIRED key；
    但 summary.registered_assets 是固定业务概念（不含 RETIRED/DISPOSED），不受 toggle 影响（spec §2.1）."""
    svc = StatsService(populated_session)
    stats = svc.get_dashboard_stats(include_retired=True)
    assert stats.status_distribution.get("RETIRED") == 1
    # registered_assets 固定 = count(status NOT IN (RETIRED, DISPOSED))，与 toggle 无关
    assert stats.summary.registered_assets == 4
    # total_assets 含 RETIRED，仍是 5
    assert stats.summary.total_assets == 5


def test_get_dashboard_stats_idle_top_ordering(populated_session):
    svc = StatsService(populated_session)
    stats = svc.get_dashboard_stats()
    assert len(stats.idle_top) == 3
    assert stats.idle_top[0].asset_code == "G-001"  # 50d
    assert stats.idle_top[0].idle_days >= 49
    assert stats.idle_top[1].asset_code == "L-001"  # 30d
    assert stats.idle_top[2].asset_code == "L-002"  # 5d


def test_get_dashboard_stats_holder_ranking_skips_null(populated_session):
    svc = StatsService(populated_session)
    stats = svc.get_dashboard_stats()
    holders = [h.holder for h in stats.holder_ranking]
    assert None not in holders
    assert "张三" in holders
    assert "李四" in holders


def test_get_dashboard_stats_fields_idle_top_only(populated_session):
    svc = StatsService(populated_session)
    stats = svc.get_dashboard_stats(fields={"idle_top"})
    assert stats.idle_top is not None
    assert stats.type_distribution is None
    assert stats.status_distribution is None
    assert stats.holder_ranking is None
    assert stats.summary is not None


def test_get_dashboard_stats_fields_multiple(populated_session):
    svc = StatsService(populated_session)
    stats = svc.get_dashboard_stats(fields={"idle_top", "status_distribution"})
    assert stats.idle_top is not None
    assert stats.status_distribution is not None
    assert stats.type_distribution is None


def test_get_dashboard_stats_fields_unknown_raises(populated_session):
    svc = StatsService(populated_session)
    with pytest.raises(ValidationError, match="fields"):
        svc.get_dashboard_stats(fields={"foo"})  # type: ignore


def test_get_dashboard_stats_idle_top_max_10(session: Session):
    """IDLE 资产 > 10 件时严格截断 10 件."""
    at = AssetType(name="Bulk", code_prefix="BK", custom_fields=[])
    session.add(at)
    session.flush()
    for i in range(15):
        a = Asset(
            asset_code=f"B-{i:03d}",
            name=f"B{i}",
            type_id=at.id,
            status=AssetStatus.IDLE,
        )
        a.created_at = datetime.now(UTC) - timedelta(days=15 - i)
        session.add(a)
    session.flush()
    stats = StatsService(session).get_dashboard_stats()
    assert len(stats.idle_top) == 10


def test_get_dashboard_stats_idle_top_under_10_no_padding(session: Session):
    """IDLE 资产 < 10 时不补位."""
    at = AssetType(name="Few", code_prefix="FW", custom_fields=[])
    session.add(at)
    session.flush()
    for i in range(3):
        session.add(
            Asset(
                asset_code=f"F-{i:03d}",
                name=f"F{i}",
                type_id=at.id,
                status=AssetStatus.IDLE,
            )
        )
    session.flush()
    stats = StatsService(session).get_dashboard_stats()
    assert len(stats.idle_top) == 3


def test_get_dashboard_stats_summary_always_returned(populated_session):
    """summary 不受 fields 控制."""
    svc = StatsService(populated_session)
    stats = svc.get_dashboard_stats(fields=set())
    assert stats.summary is not None
    assert stats.idle_top is None


def test_get_dashboard_stats_fields_none_returns_all_segments(populated_session):
    """fields=None（默认）→ 4 段全返；fields=set() → 4 段全 None.
    contract：None 表示 'all'，不同于空集合 'none'."""
    svc = StatsService(populated_session)
    stats = svc.get_dashboard_stats()  # fields=None
    assert stats.type_distribution is not None
    assert stats.status_distribution is not None
    assert stats.holder_ranking is not None
    assert stats.idle_top is not None
    assert stats.summary is not None
