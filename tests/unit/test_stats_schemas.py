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
        name="A100 显卡",
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
            total_assets=0,
            registered_assets=0,
            idle_count=0,
            include_retired=False,
            include_disposed=False,
            generated_at=datetime.now(),
        )
    )
    assert s.idle_top is None
    assert s.type_distribution is None


def test_stats_read_full_payload():
    s = StatsRead(
        type_distribution=[
            TypeDistributionItem(type_id=uuid4(), type_name="Laptop", count=71)
        ],
        status_distribution={"IDLE": 78, "IN_USE": 92},
        holder_ranking=[HolderRankingItem(holder="张三", count=28)],
        idle_top=[],
        summary=StatsSummary(
            total_assets=187,
            registered_assets=182,
            idle_count=78,
            include_retired=False,
            include_disposed=False,
            generated_at=datetime.now(),
        ),
    )
    assert len(s.type_distribution) == 1
    assert s.holder_ranking[0].holder == "张三"


def test_stats_summary_naive_datetime_coerced_to_utc():
    """spec §2.1 要求 generated_at 是 ISO-8601 with Z；naive datetime 应自动加 UTC tz."""
    s = StatsSummary(
        total_assets=10,
        registered_assets=10,
        idle_count=5,
        include_retired=False,
        include_disposed=False,
        generated_at=datetime(2026, 5, 6, 10, 30, 0),  # naive
    )
    assert s.generated_at.tzinfo is not None
    # 序列化后含 Z 或 +00:00
    serialized = s.model_dump(mode="json")["generated_at"]
    assert "Z" in serialized or "+00:00" in serialized


def test_idle_top_item_naive_datetime_coerced_to_utc():
    """idle_since 同理."""
    item = IdleTopItem(
        asset_id=uuid4(),
        asset_code="X-001",
        name="X 资产",
        type_name="X",
        current_location=None,
        idle_days=10,
        idle_since=datetime(2025, 12, 4),  # naive
    )
    assert item.idle_since.tzinfo is not None
