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
            msg = str(e).lower()
            if "asset_code" in msg:
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
        row = self.session.exec(stmt).first()
        # session.exec(select(func.max(...))) 返回单元素 Row（不是 tuple 子类），需要解包
        if row is None:
            max_code = None
        elif hasattr(row, "_mapping") or isinstance(row, tuple):
            max_code = row[0]
        else:
            max_code = row
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
    ) -> list[Asset]:
        return self.repo.list_filtered(type_id=type_id, status=status, holder=holder, q=q)

    def update_asset(
        self,
        asset_id: uuid.UUID,
        name: str | None = None,
        serial_number: str | _Unset = _UNSET,
        status: AssetStatus | None = None,
        holder: str | _Unset = _UNSET,
        location: str | _Unset = _UNSET,
        notes: str | _Unset = _UNSET,
        custom_data: dict | _Unset = _UNSET,
        acquired_at: date | None | _Unset = _UNSET,
    ) -> Asset:
        a = self.get_asset(asset_id)
        if name is not None:
            a.name = name
        if not isinstance(serial_number, _Unset):
            a.serial_number = serial_number
        if status is not None:
            # state_machine 是 Task 5 才创建的模块；用 try-import 兜底，让本 Task 不阻塞
            try:
                from asset_hub.services.state_machine import assert_transition_allowed

                assert_transition_allowed(a.status, status)
            except ImportError:
                pass  # Task 5 落地后这条 import 会成功，自动生效
            a.status = status
        if not isinstance(holder, _Unset):
            a.holder = holder
        if not isinstance(location, _Unset):
            a.location = location
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
        # cascade 在 Task 6 接通；本 step 占位仅删 asset
        a = self.get_asset(asset_id)
        self.repo.delete(a)
        self.session.commit()
