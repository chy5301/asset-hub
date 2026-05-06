import uuid
from datetime import UTC, date, datetime

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session

from asset_hub.errors import DuplicateError, NotFoundError
from asset_hub.models.asset import Asset, AssetStatus
from asset_hub.repositories.asset import AssetRepository
from asset_hub.repositories.asset_type import TypeRepository
from asset_hub.services.validation import validate_custom_data


class _Unset:
    pass


_UNSET = _Unset()


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
    ) -> list[Asset]:
        return self.repo.list_filtered(
            type_id=type_id,
            status=status,
            holder=holder,
            q=q,
            include_retired=include_retired,
            include_disposed=include_disposed,
        )

    def annotate_idle_days(self, assets: list[Asset]) -> list[Asset]:
        """给 IDLE 资产填充 idle_days；in-place 设属性，让 AssetRead 序列化能读到。"""
        from asset_hub.services._idle_days import compute_idle_days_for_asset

        for a in assets:
            if a.status == AssetStatus.IDLE:
                # @property 是只读的，用 setattr 注入实例属性供 @property 读取
                setattr(a, "_idle_days_value", compute_idle_days_for_asset(self.session, a.id))
            else:
                setattr(a, "_idle_days_value", None)
        return assets

    def update_asset(
        self,
        asset_id: uuid.UUID,
        name: str | None = None,
        serial_number: str | _Unset = _UNSET,
        notes: str | _Unset = _UNSET,
        custom_data: dict | _Unset = _UNSET,
        acquired_at: date | None | _Unset = _UNSET,
    ) -> Asset:
        """更新资产非状态字段。

        M3a 后 status/holder/location 不再走 PATCH——必须通过
        POST /api/assets/{id}/transitions 经 state machine 校验。
        """
        a = self.get_asset(asset_id)
        if name is not None:
            a.name = name
        if not isinstance(serial_number, _Unset):
            a.serial_number = serial_number
        if not isinstance(notes, _Unset):
            a.notes = notes
        if not isinstance(custom_data, _Unset):
            asset_type = self.type_repo.get(a.type_id)
            a.custom_data = validate_custom_data(asset_type.custom_fields, custom_data)
        if not isinstance(acquired_at, _Unset):
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
