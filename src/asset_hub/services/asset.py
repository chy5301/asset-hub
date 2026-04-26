import uuid
from datetime import UTC, date, datetime

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session

from asset_hub.errors import DuplicateError, NotFoundError
from asset_hub.models.asset import Asset, AssetStatus
from asset_hub.repositories.asset import AssetRepository
from asset_hub.repositories.asset_type import TypeRepository
from asset_hub.services.state_machine import assert_transition_allowed
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
            assert_transition_allowed(a.status, status)
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
            # update_asset 不改 asset_code（register 才生成），SN 是唯一 unique 约束
            # 故无需像 register 那样嗅探 e.orig.args[0]
            self.session.rollback()
            raise DuplicateError(f"序列号重复: {serial_number}") from None
        self.session.refresh(a)
        return a

    def change_status(self, asset_id: uuid.UUID, to_status: AssetStatus) -> Asset:
        """状态切换。state_machine 兜底转换合法性。

        本方法不写 CheckoutRecord——只用于 §14.5 的 4 个轻量状态切换：
        送修 / 修好回库 / 退役 / 重新启用。派发/归还仍走 CheckoutService。
        """
        a = self.get_asset(asset_id)
        assert_transition_allowed(a.status, to_status)
        a.status = to_status
        a.updated_at = datetime.now(UTC)
        self.session.commit()
        self.session.refresh(a)
        return a

    def delete_asset(self, asset_id: uuid.UUID) -> None:
        """硬删除：cascade 清掉 CheckoutRecord + Attachment（FS 文件 + DB 元数据）。

        spec D17：service 层显式 cascade。CheckoutRecord 业务上仅对 asset 有意义；
        Attachment 已和 asset 绑定。

        Note: 派发中（IN_USE）资产删除前端 disable + tooltip "需先归还"；
        本方法不再做 status 检查，由 router 层防护（D16）。前端如绕过，
        走到这里仍会成功——cascade 删除当前 CheckoutRecord 也是合理行为。
        """
        # 局部 import 避免 services 顶层依赖 api/storage 包初始化顺序
        from sqlalchemy import delete as sa_delete

        from asset_hub.models.checkout import CheckoutRecord
        from asset_hub.services.attachment import AttachmentService
        from asset_hub.storage import get_default_storage

        a = self.get_asset(asset_id)

        # 先删附件（外部资源 FS 文件需要）
        att_svc = AttachmentService(self.session, get_default_storage())
        for att in att_svc.list(asset_id=asset_id):
            att_svc.delete(att.id)  # 内部已处理 FS 删除 + DB 元数据

        # 解绑 current_checkout_id 防外键阻塞 CheckoutRecord 批删
        a.current_checkout_id = None
        self.session.flush()

        # 再删 CheckoutRecord（仍在同 session 事务）
        self.session.exec(
            sa_delete(CheckoutRecord).where(CheckoutRecord.asset_id == asset_id)
        )

        self.repo.delete(a)
        self.session.commit()
