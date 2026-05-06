from datetime import datetime
from uuid import uuid4

from asset_hub.api.schemas.stats import (
    HolderRankingItem,
    IdleTopItem,
    StatsField,
    StatsRead,
    StatsSummary,
    TypeDistributionItem,
)


def test_stats_field_literal_values():
    """StatsField 必须是 4 段名固定字面量."""
    valid: StatsField = "idle_top"
    assert valid == "idle_top"


def test_stats_summary_required_fields():
    s = StatsSummary(
        total_assets=187,
        registered_assets=182,
        idle_count=78,
        include_retired=False,
        include_disposed=False,
        generated_at=datetime(2026, 5, 6, 10, 30, 0),
    )
    assert s.total_assets == 187
    assert s.registered_assets == 182


def test_idle_top_item_required_fields():
    item = IdleTopItem(
        asset_id=uuid4(),
        asset_code="GPU-A100-03",
        type_name="GPU",
        current_location="仓库",
        idle_days=152,
        idle_since=datetime(2025, 12, 4),
    )
    assert item.idle_days == 152


def test_stats_read_all_sections_optional():
    """所有段都是 optional，summary 必填."""
    s = StatsRead(
        summary=StatsSummary(
            total_assets=0, registered_assets=0, idle_count=0,
            include_retired=False, include_disposed=False,
            generated_at=datetime.now(),
        )
    )
    assert s.idle_top is None
    assert s.type_distribution is None


def test_stats_read_full_payload():
    s = StatsRead(
        type_distribution=[TypeDistributionItem(type_id=uuid4(), type_name="Laptop", count=71)],
        status_distribution={"IDLE": 78, "IN_USE": 92},
        holder_ranking=[HolderRankingItem(holder="张三", count=28)],
        idle_top=[],
        summary=StatsSummary(
            total_assets=187, registered_assets=182, idle_count=78,
            include_retired=False, include_disposed=False,
            generated_at=datetime.now(),
        ),
    )
    assert len(s.type_distribution) == 1
    assert s.holder_ranking[0].holder == "张三"
