import uuid
from datetime import UTC, date, datetime
from typing import Literal

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session

from asset_hub.errors import DuplicateError, NotFoundError, ValidationError
from asset_hub.models.asset import Asset, AssetStatus
from asset_hub.repositories.asset import AssetRepository
from asset_hub.repositories.asset_type import TypeRepository
from asset_hub.services._common import UNSET, UnsetType
from asset_hub.services._idle_days import ensure_aware, idle_since_expr, last_idle_subq
from asset_hub.services.validation import validate_custom_data

SortOrder = Literal["asc", "desc"]
SortByField = Literal["name", "asset_code", "created_at", "updated_at", "acquired_at", "idle_days"]
SORT_FIELD_WHITELIST = frozenset({
    "name", "asset_code", "created_at", "updated_at", "acquired_at", "idle_days",
})
LIMIT_MAX = 1000


class AssetService:
    def __init__(self, session: Session):
        self.session = session
        self.repo = AssetRepository(session)
        self.type_repo = TypeRepository(session)

    def register(
        self,
        name: str,
        type_id: uuid.UUID,
        custom_data: dict,
        serial_number: str | None = None,
        holder: str | None = None,
        location: str | None = None,
        notes: str | None = None,
        acquired_at: date | None = None,
    ) -> Asset:
        asset_type = self.type_repo.get(type_id)
        if asset_type is None:
            raise NotFoundError(f"类型不存在: {type_id}")

        validated_data = validate_custom_data(asset_type.custom_fields, custom_data)
        asset_code = self._generate_asset_code(asset_type.code_prefix, type_id)

        asset = Asset(
            asset_code=asset_code,
            name=name,
            type_id=type_id,
            serial_number=serial_number,
            holder=holder,
            location=location,
            notes=notes,
            custom_data=validated_data,
            acquired_at=acquired_at,
        )
        try:
            self.repo.add(asset)
            self.session.commit()
        except IntegrityError as e:
            self.session.rollback()
            orig_msg = (
                str(e.orig.args[0]).lower()
                if e.orig and e.orig.args
                else str(e).lower()
            )
            if "asset_code" in orig_msg:
                # 极小概率：同 type 极高并发，两个 register 各自 max+1 算到同一值
                raise DuplicateError(f"asset_code 撞车（请重试）: {asset_code}") from None
            raise DuplicateError(f"序列号重复: {serial_number}") from None
        self.session.refresh(asset)
        return asset

    def _generate_asset_code(self, prefix: str, type_id: uuid.UUID) -> str:
        """{prefix}-{per_type_max+1:03d}。

        v1 单用户场景，并发风险近零；如需强一致可在 SELECT MAX 外加 SELECT FOR UPDATE
        或 INSERT 失败重试一次。本里程碑选择最简：失败 → DuplicateError → 调用方重试。
        """
        stmt = select(func.max(Asset.asset_code)).where(Asset.type_id == type_id)
        max_code = self.session.scalar(stmt)
        if max_code is None:
            seq = 1
        else:
            try:
                seq = int(max_code.split("-")[-1]) + 1
            except (ValueError, AttributeError):
                seq = 1
        return f"{prefix}-{seq:03d}"

    def get_asset(self, asset_id: uuid.UUID) -> Asset:
        a = self.repo.get(asset_id)
        if a is None:
            raise NotFoundError(f"资产不存在: {asset_id}")
        return a

    def list_assets(
        self,
        type_id: uuid.UUID | None = None,
        status: AssetStatus | None = None,
        holder: str | None = None,
        q: str | None = None,
        include_retired: bool = False,
        include_disposed: bool = False,
        sort_by: str | None = None,
        sort_order: SortOrder = "desc",
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[Asset]:
        if sort_by is not None and sort_by not in SORT_FIELD_WHITELIST:
            raise ValidationError(
                f"sort_by 不支持：{sort_by!r}，可选：{sorted(SORT_FIELD_WHITELIST)}"
            )
        # Router 用 Literal 已自动 422；此 guard 兜底 CLI / 直接调用 service 的 caller
        if sort_order not in ("asc", "desc"):
            raise ValidationError(f"sort_order 必须是 'asc' 或 'desc'，收到：{sort_order!r}")
        if offset is not None and offset < 0:
            raise ValidationError(f"offset 不能为负，收到：{offset}")
        if limit is not None and (limit < 1 or limit > LIMIT_MAX):
            raise ValidationError(f"limit 必须在 1..{LIMIT_MAX}，收到：{limit}")

        return self.repo.list_filtered(
            type_id=type_id,
            status=status,
            holder=holder,
            q=q,
            include_retired=include_retired,
            include_disposed=include_disposed,
            sort_by=sort_by,
            sort_order=sort_order,
            limit=limit,
            offset=offset,
        )

    def annotate_idle_days(self, assets: list[Asset]) -> list[Asset]:
        """批量计算 idle_days 注入 _idle_days_value instance attr。

        单 SQL 批量查，避免 N+1（list 100 IDLE assets 不会触发 200 queries）。
        复用 last_idle_subq + idle_since_expr 与 stats / sort_by=idle_days 同源。
        """
        idle_asset_ids = [a.id for a in assets if a.status == AssetStatus.IDLE]

        days_by_id: dict[uuid.UUID, int | None] = {}
        if idle_asset_ids:
            sq = last_idle_subq()
            stmt = (
                select(Asset.id, idle_since_expr(Asset, sq))
                .select_from(Asset)
                .join(sq, sq.c.asset_id == Asset.id, isouter=True)
                .where(Asset.id.in_(idle_asset_ids))
            )
            now = datetime.now(UTC)
            for asset_id, idle_since in self.session.exec(stmt).all():
                if idle_since is None:
                    days_by_id[asset_id] = None
                    continue
                days_by_id[asset_id] = int((now - ensure_aware(idle_since)).total_seconds() // 86400)

        for a in assets:
            if a.status == AssetStatus.IDLE:
                setattr(a, "_idle_days_value", days_by_id.get(a.id))
            else:
                setattr(a, "_idle_days_value", None)
        return assets

    def update_asset(
        self,
        asset_id: uuid.UUID,
        name: str | None = None,
        serial_number: str | UnsetType = UNSET,
        notes: str | UnsetType = UNSET,
        custom_data: dict | UnsetType = UNSET,
        acquired_at: date | None | UnsetType = UNSET,
    ) -> Asset:
        """更新资产非状态字段。

        M3a 后 status/holder/location 不再走 PATCH——必须通过
        POST /api/assets/{id}/transitions 经 state machine 校验。
        """
        a = self.get_asset(asset_id)
        if name is not None:
            a.name = name
        if not isinstance(serial_number, UnsetType):
            a.serial_number = serial_number
        if not isinstance(notes, UnsetType):
            a.notes = notes
        if not isinstance(custom_data, UnsetType):
            asset_type = self.type_repo.get(a.type_id)
            a.custom_data = validate_custom_data(asset_type.custom_fields, custom_data)
        if not isinstance(acquired_at, UnsetType):
            a.acquired_at = acquired_at
        a.updated_at = datetime.now(UTC)
        try:
            self.session.commit()
        except IntegrityError:
            self.session.rollback()
            raise DuplicateError(f"序列号重复: {serial_number}") from None
        self.session.refresh(a)
        return a

    def delete_asset(self, asset_id: uuid.UUID) -> None:
        """硬删除：cascade 清掉 StateTransitionRecord + Attachment。"""
        from sqlalchemy import delete as sa_delete

        from asset_hub.models.state_transition import StateTransitionRecord
        from asset_hub.services.attachment import AttachmentService
        from asset_hub.storage import get_default_storage

        a = self.get_asset(asset_id)

        att_svc = AttachmentService(self.session, get_default_storage())
        for att in att_svc.list(asset_id=asset_id):
            att_svc.delete(att.id)

        self.session.exec(
            sa_delete(StateTransitionRecord).where(StateTransitionRecord.asset_id == asset_id)
        )

        self.repo.delete(a)
        self.session.commit()
