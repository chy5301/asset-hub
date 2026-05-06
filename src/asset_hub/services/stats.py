"""M3b 看板 stats service。

4 段聚合 + summary 业务摘要；fields 子集查询省 token。
idle_top 复用 services/_idle_days helper（与 list_assets 同源）。
"""
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlmodel import Session

from asset_hub.api.schemas.stats import (
    HolderRankingItem,
    IdleTopItem,
    StatsField,
    StatsRead,
    StatsSummary,
    TypeDistributionItem,
)
from asset_hub.errors import ValidationError
from asset_hub.models.asset import Asset, AssetStatus
from asset_hub.models.asset_type import AssetType
from asset_hub.services._idle_days import ensure_aware, idle_since_expr, last_idle_subq

ALL_FIELDS: frozenset[StatsField] = frozenset({
    "type_distribution", "status_distribution", "holder_ranking", "idle_top",
})


class StatsService:
    def __init__(self, session: Session):
        self.session = session

    def get_dashboard_stats(
        self,
        *,
        include_retired: bool = False,
        include_disposed: bool = False,
        fields: set[StatsField] | None = None,
    ) -> StatsRead:
        if fields is not None:
            unknown = fields - ALL_FIELDS
            if unknown:
                raise ValidationError(
                    f"fields 含未知段：{sorted(unknown)}；可选：{sorted(ALL_FIELDS)}"
                )
        wanted = fields if fields is not None else ALL_FIELDS

        type_dist = (
            self._type_distribution(include_retired, include_disposed)
            if "type_distribution" in wanted
            else None
        )
        status_dist = (
            self._status_distribution(include_retired, include_disposed)
            if "status_distribution" in wanted
            else None
        )
        holders = (
            self._holder_ranking(include_retired, include_disposed)
            if "holder_ranking" in wanted
            else None
        )
        idle = self._idle_top(limit=10) if "idle_top" in wanted else None
        summary = self._summary(include_retired, include_disposed)

        return StatsRead(
            type_distribution=type_dist,
            status_distribution=status_dist,
            holder_ranking=holders,
            idle_top=idle,
            summary=summary,
        )

    def _base_filter(self, stmt, include_retired: bool, include_disposed: bool):
        if not include_retired:
            stmt = stmt.where(Asset.status != AssetStatus.RETIRED)
        if not include_disposed:
            stmt = stmt.where(Asset.status != AssetStatus.DISPOSED)
        return stmt

    def _type_distribution(self, ir: bool, idp: bool) -> list[TypeDistributionItem]:
        stmt = (
            select(Asset.type_id, AssetType.name, func.count(Asset.id))
            .join(AssetType, AssetType.id == Asset.type_id)
            .group_by(Asset.type_id, AssetType.name)
            .order_by(func.count(Asset.id).desc())
        )
        stmt = self._base_filter(stmt, ir, idp)
        return [
            TypeDistributionItem(type_id=tid, type_name=name, count=cnt)
            for tid, name, cnt in self.session.exec(stmt).all()
        ]

    def _status_distribution(self, ir: bool, idp: bool) -> dict[str, int]:
        stmt = select(Asset.status, func.count(Asset.id)).group_by(Asset.status)
        stmt = self._base_filter(stmt, ir, idp)
        return {status.value: count for status, count in self.session.exec(stmt).all()}

    def _holder_ranking(self, ir: bool, idp: bool) -> list[HolderRankingItem]:
        stmt = (
            select(Asset.holder, func.count(Asset.id))
            .where(Asset.holder.is_not(None))
            .group_by(Asset.holder)
            .order_by(func.count(Asset.id).desc())
        )
        stmt = self._base_filter(stmt, ir, idp)
        return [
            HolderRankingItem(holder=h, count=cnt)
            for h, cnt in self.session.exec(stmt).all()
            if h is not None  # belt-and-suspenders；WHERE 已排除 NULL，但保险起见
        ]

    def _idle_top(self, limit: int) -> list[IdleTopItem]:
        sq = last_idle_subq()
        idle_since = idle_since_expr(Asset, subq=sq)
        stmt = (
            select(Asset.id, Asset.asset_code, AssetType.name, Asset.location, idle_since)
            .join(AssetType, AssetType.id == Asset.type_id)
            .outerjoin(sq, sq.c.asset_id == Asset.id)
            .where(Asset.status == AssetStatus.IDLE)
            .order_by(idle_since.asc())
            .limit(limit)
        )
        now = datetime.now(UTC)
        items = []
        for aid, code, type_name, location, since in self.session.exec(stmt).all():
            since_aware = ensure_aware(since)
            days = int((now - since_aware).total_seconds() // 86400)
            items.append(IdleTopItem(
                asset_id=aid,
                asset_code=code,
                type_name=type_name,
                current_location=location,
                idle_days=days,
                idle_since=since_aware,
            ))
        return items

    def _summary(self, ir: bool, idp: bool) -> StatsSummary:
        total = self.session.exec(select(func.count(Asset.id))).scalar_one()
        registered = self.session.exec(
            select(func.count(Asset.id)).where(
                Asset.status != AssetStatus.RETIRED,
                Asset.status != AssetStatus.DISPOSED,
            )
        ).scalar_one()
        idle_count = self.session.exec(
            select(func.count(Asset.id)).where(Asset.status == AssetStatus.IDLE)
        ).scalar_one()
        return StatsSummary(
            total_assets=total,
            registered_assets=registered,
            idle_count=idle_count,
            include_retired=ir,
            include_disposed=idp,
            generated_at=datetime.now(UTC),
        )
