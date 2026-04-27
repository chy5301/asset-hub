import uuid
from datetime import UTC, datetime

from sqlmodel import Session

from asset_hub.errors import StateError, ValidationError
from asset_hub.models.asset import AssetStatus
from asset_hub.models.checkout import CheckoutRecord
from asset_hub.repositories.checkout import CheckoutRepository
from asset_hub.services.asset import AssetService
from asset_hub.services.state_machine import assert_transition_allowed


class CheckoutService:
    def __init__(self, session: Session):
        self.session = session
        self.repo = CheckoutRepository(session)
        self.asset_svc = AssetService(session)

    def checkout(
        self,
        asset_id: uuid.UUID,
        holder: str,
        location: str | None = None,
        note: str | None = None,
    ) -> CheckoutRecord:
        asset = self.asset_svc.get_asset(asset_id)

        # 保留既有的精细错误文案（既有测试断言"已派发"/"RETIRED"/"MAINTENANCE"）；
        # state_machine 作兜底（其他不合法转换走 ValidationError → StateError）。
        if asset.status == AssetStatus.IN_USE:
            raise StateError(f"资产已派发，请先归还: {asset_id}")
        if asset.status in (AssetStatus.RETIRED, AssetStatus.MAINTENANCE):
            raise StateError(
                f"资产状态 {asset.status.value} 不允许派发: {asset_id}"
            )
        try:
            assert_transition_allowed(asset.status, AssetStatus.IN_USE)
        except ValidationError as e:
            raise StateError(str(e)) from e

        now = datetime.now(UTC)
        record = CheckoutRecord(
            asset_id=asset_id,
            holder=holder,
            location=location,
            checkout_note=note,
        )
        self.repo.add(record)
        self.session.flush()  # record.id 可用，便于设 current_checkout_id

        asset.status = AssetStatus.IN_USE
        asset.holder = holder
        asset.location = location
        asset.current_checkout_id = record.id  # 反规范化字段
        asset.updated_at = now

        self.session.commit()
        self.session.refresh(record)
        return record

    def return_(
        self,
        asset_id: uuid.UUID,
        note: str | None = None,
    ) -> CheckoutRecord:
        asset = self.asset_svc.get_asset(asset_id)

        record = self.repo.find_open_by_asset(asset_id)
        if record is None:
            raise StateError(f"资产无未归还记录: {asset_id}")

        try:
            assert_transition_allowed(asset.status, AssetStatus.IDLE)
        except ValidationError as e:
            raise StateError(str(e)) from e

        now = datetime.now(UTC)
        record.returned_at = now
        record.return_note = note

        asset.status = AssetStatus.IDLE
        asset.holder = None
        asset.location = None
        asset.current_checkout_id = None  # 清空
        asset.updated_at = now

        self.session.commit()
        self.session.refresh(record)
        return record

    def history(self, asset_id: uuid.UUID) -> list[CheckoutRecord]:
        self.asset_svc.get_asset(asset_id)
        return self.repo.list_by_asset(asset_id)
