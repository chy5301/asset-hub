import uuid

from sqlalchemy import asc, desc
from sqlmodel import Session, select

from asset_hub.models.asset import Asset, AssetStatus
from asset_hub.services._idle_days import idle_since_expr, last_idle_subq

# 显式映射允许的排序列；getattr(Asset, ...) 在 idle_days 等 @property 上会返回
# 描述符而非 ORM 列，导致 SQLAlchemy 报 AttributeError 或生成无效 SQL。
# idle_days 故意不在此 map——idle_days 走上面的 outerjoin 分支单独处理。
_SORT_COLUMN_MAP: dict[str, object] = {
    "name": Asset.name,
    "asset_code": Asset.asset_code,
    "created_at": Asset.created_at,
    "updated_at": Asset.updated_at,
    "acquired_at": Asset.acquired_at,
}


class AssetRepository:
    def __init__(self, session: Session):
        self.session = session

    def add(self, asset: Asset) -> Asset:
        self.session.add(asset)
        self.session.flush()
        return asset

    def get(self, asset_id: uuid.UUID) -> Asset | None:
        return self.session.get(Asset, asset_id)

    def delete(self, asset: Asset) -> None:
        self.session.delete(asset)
        self.session.flush()

    def list_filtered(
        self,
        type_id: uuid.UUID | None = None,
        status: AssetStatus | None = None,
        holder: str | None = None,
        q: str | None = None,
        include_retired: bool = False,
        include_disposed: bool = False,
        sort_by: str | None = None,
        sort_order: str = "desc",
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[Asset]:
        stmt = select(Asset)
        if type_id is not None:
            stmt = stmt.where(Asset.type_id == type_id)
        if status is not None:
            stmt = stmt.where(Asset.status == status)
        else:
            # 默认隐藏 RETIRED / DISPOSED，按 toggle 决定是否包含
            excluded = []
            if not include_retired:
                excluded.append(AssetStatus.RETIRED)
            if not include_disposed:
                excluded.append(AssetStatus.DISPOSED)
            if excluded:
                stmt = stmt.where(Asset.status.notin_(excluded))
        if holder is not None:
            stmt = stmt.where(Asset.holder == holder)
        if q is not None:
            stmt = stmt.where(
                Asset.name.contains(q)
                | Asset.serial_number.contains(q)
                | Asset.notes.contains(q)
                | Asset.asset_code.contains(q)
            )

        # 排序：sort_by 显式传入时按用户指定；否则保留现有默认 asset_code.asc()
        if sort_by == "idle_days":
            sq = last_idle_subq()
            # idle_days desc ≡ idle_since asc（越早 idle 越久 = idle_days 越大）
            # idle_days asc ≡ idle_since desc
            idle_since = idle_since_expr(Asset, subq=sq)
            sort_dir = asc if sort_order == "desc" else desc
            stmt = stmt.outerjoin(sq, sq.c.asset_id == Asset.id).order_by(sort_dir(idle_since))
        elif sort_by is not None:
            col = _SORT_COLUMN_MAP.get(sort_by)
            if col is None:
                # service 层已 whitelist；防御：repo 被直调且传未知 sort_by 时落回默认
                stmt = stmt.order_by(Asset.asset_code.asc())
            else:
                direction = desc if sort_order == "desc" else asc
                stmt = stmt.order_by(direction(col))
        else:
            # 默认按 asset_code 升序——保持 Task 4 之前的行为；
            # plan 模板写过 created_at desc，但改默认会破坏现有 caller / 测试，
            # 故保留 asset_code asc。要其它顺序 → 显式传 sort_by。
            stmt = stmt.order_by(Asset.asset_code.asc())

        # limit/offset
        if offset is not None:
            stmt = stmt.offset(offset)
        if limit is not None:
            stmt = stmt.limit(limit)

        return list(self.session.exec(stmt).all())
