"""idle_days 计算：从 StateTransitionRecord 取上次 to_status=IDLE 的 created_at；
新登记后未发生 transition 的 IDLE 资产 fallback Asset.created_at。

提供两种用法：
- compute_idle_days_for_asset(): 单 asset 标量查询（list/detail DTO 用）
- idle_since_expr(): 可拼到 select(Asset).join(...).order_by() 的子查询表达式
  （stats 闲置 Top 10 / list_assets sort_by=idle_days 用）
"""
import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.sql.functions import Function
from sqlalchemy.sql.selectable import Subquery
from sqlmodel import Session

from asset_hub.models.asset import Asset, AssetStatus
from asset_hub.models.state_transition import StateTransitionRecord


def _last_idle_subq():
    """子查询：每个 asset 上次进入 IDLE 的时间."""
    return (
        select(
            StateTransitionRecord.asset_id.label("asset_id"),
            func.max(StateTransitionRecord.created_at).label("last_idle_at"),
        )
        .where(StateTransitionRecord.to_status == AssetStatus.IDLE)
        .group_by(StateTransitionRecord.asset_id)
        .subquery()
    )


def idle_since_expr(
    asset_alias: type[Asset] = Asset,
    last_idle_subq: Subquery | None = None,
) -> Function:
    """COALESCE(last_idle_at, asset.created_at) 表达式 — 用作排序/选择列."""
    sq = last_idle_subq if last_idle_subq is not None else _last_idle_subq()
    return func.coalesce(sq.c.last_idle_at, asset_alias.created_at)


def compute_idle_days_for_asset(session: Session, asset_id: uuid.UUID) -> int | None:
    """返回某资产的 idle_days；非 IDLE 状态返 None。"""
    asset = session.get(Asset, asset_id)
    if asset is None or asset.status != AssetStatus.IDLE:
        return None

    sq = _last_idle_subq()
    stmt = select(idle_since_expr(Asset, sq)).select_from(Asset).join(
        sq, sq.c.asset_id == Asset.id, isouter=True,
    ).where(Asset.id == asset_id)
    idle_since: datetime | None = session.exec(stmt).scalar_one_or_none()
    if idle_since is None:
        return None
    delta = datetime.now(UTC) - _ensure_aware(idle_since)
    return int(delta.total_seconds() // 86400)


def _ensure_aware(dt: datetime) -> datetime:
    """SQLite 取出来可能是 naive；统一为 UTC aware."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt
