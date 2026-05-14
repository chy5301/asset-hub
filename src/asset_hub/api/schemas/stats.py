"""M3b 看板 / stats 端点 DTO."""

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from asset_hub.api.schemas._datetime import UtcDatetime

# 4 段名 — fields 参数 + service 函数签名都引用
StatsField = Literal[
    "type_distribution",
    "status_distribution",
    "holder_ranking",
    "idle_top",
]


class TypeDistributionItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    type_id: UUID
    type_name: str
    count: int


class HolderRankingItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    holder: str
    count: int


class IdleTopItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    asset_id: UUID
    asset_code: str
    type_name: str | None
    current_location: str | None
    idle_days: int
    idle_since: UtcDatetime


class StatsSummary(BaseModel):
    """业务摘要——命名 summary 而非 metadata，避免与 CLI envelope 顶层 metadata 冲突."""

    total_assets: int
    registered_assets: int
    idle_count: int
    include_retired: bool
    include_disposed: bool
    generated_at: UtcDatetime


class StatsRead(BaseModel):
    """4 段聚合响应 + summary。各段在响应里通过 fields 子集控制；summary 始终返回."""

    model_config = ConfigDict(from_attributes=True)

    type_distribution: list[TypeDistributionItem] | None = None
    status_distribution: dict[str, int] | None = None
    holder_ranking: list[HolderRankingItem] | None = None
    idle_top: list[IdleTopItem] | None = None
    summary: StatsSummary
