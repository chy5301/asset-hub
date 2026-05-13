"""验证 AssetRead.idle_days 与 stats.idle_top.idle_days 同源."""

from datetime import UTC, datetime, timedelta

from sqlmodel import Session

from asset_hub.api.schemas.asset import AssetRead
from asset_hub.models.asset import Asset, AssetStatus
from asset_hub.models.asset_type import AssetType
from asset_hub.models.state_transition import StateTransitionRecord, TransitionKind
from asset_hub.services.asset import AssetService
from asset_hub.services.stats import StatsService


def test_assetread_idle_days_matches_stats_idle_top(session: Session):
    """同一 IDLE 资产在 list 路径 (annotate_idle_days) 与 stats idle_top 的 idle_days 应一致."""
    at = AssetType(name="LRR", code_prefix="LRR", custom_fields=[])
    session.add(at)
    session.flush()
    a = Asset(asset_code="LRR-001", name="L1", type_id=at.id, status=AssetStatus.IDLE)
    session.add(a)
    session.flush()
    session.add(
        StateTransitionRecord(
            asset_id=a.id,
            kind=TransitionKind.RETURN,
            from_status=AssetStatus.IN_USE,
            to_status=AssetStatus.IDLE,
            created_at=datetime.now(UTC) - timedelta(days=42),
        )
    )
    session.flush()

    asset_svc = AssetService(session)
    stats_svc = StatsService(session)

    annotated = asset_svc.annotate_idle_days([a])[0]
    list_days = AssetRead.model_validate(annotated).idle_days

    stats = stats_svc.get_dashboard_stats(fields={"idle_top"})
    stats_days = stats.idle_top[0].idle_days

    assert list_days == stats_days
    assert list_days == 42  # 容许 ±1 但本测试 fixture timestamp 精确


def test_in_use_asset_idle_days_is_none(session: Session):
    """非 IDLE 资产 idle_days 必须为 None（AssetRead 序列化）."""
    at = AssetType(name="LIU", code_prefix="LIU", custom_fields=[])
    session.add(at)
    session.flush()
    a = Asset(
        asset_code="LIU-001",
        name="L2",
        type_id=at.id,
        status=AssetStatus.IN_USE,
        holder="X",
    )
    session.add(a)
    session.flush()

    annotated = AssetService(session).annotate_idle_days([a])[0]
    assert AssetRead.model_validate(annotated).idle_days is None
