import uuid
from datetime import UTC, datetime

from sqlmodel import Session

from asset_hub.errors import NotFoundError, StateError
from asset_hub.models.asset import AssetStatus
from asset_hub.models.checkout import CheckoutRecord
from asset_hub.repositories.asset import AssetRepository
from asset_hub.repositories.checkout import CheckoutRepository


class CheckoutService:
    def __init__(self, session: Session):
        self.session = session
        self.repo = CheckoutRepository(session)
        self.asset_repo = AssetRepository(session)

    def checkout(
        self,
        asset_id: uuid.UUID,
        holder: str,
        location: str | None = None,
        note: str | None = None,
    ) -> CheckoutRecord:
        asset = self.asset_repo.get(asset_id)
        if asset is None:
            raise NotFoundError(f"资产不存在: {asset_id}")

        if asset.status == AssetStatus.IN_USE:
            raise StateError(f"资产已派发，请先归还: {asset_id}")
        if asset.status in (AssetStatus.RETIRED, AssetStatus.MAINTENANCE):
            raise StateError(
                f"资产状态 {asset.status.value} 不允许派发: {asset_id}"
            )

        record = CheckoutRecord(
            asset_id=asset_id,
            holder=holder,
            location=location,
            checkout_note=note,
        )
        self.repo.add(record)

        asset.status = AssetStatus.IN_USE
        asset.holder = holder
        asset.location = location
        asset.updated_at = datetime.now(UTC)

        self.session.commit()
        self.session.refresh(record)
        return record

    def return_(
        self,
        asset_id: uuid.UUID,
        note: str | None = None,
    ) -> CheckoutRecord:
        asset = self.asset_repo.get(asset_id)
        if asset is None:
            raise NotFoundError(f"资产不存在: {asset_id}")

        record = self.repo.find_open_by_asset(asset_id)
        if record is None:
            raise StateError(f"资产无未归还记录: {asset_id}")

        record.returned_at = datetime.now(UTC)
        record.return_note = note

        asset.status = AssetStatus.IDLE
        asset.holder = None
        asset.location = None
        asset.updated_at = datetime.now(UTC)

        self.session.commit()
        self.session.refresh(record)
        return record

    def history(self, asset_id: uuid.UUID) -> list[CheckoutRecord]:
        asset = self.asset_repo.get(asset_id)
        if asset is None:
            raise NotFoundError(f"资产不存在: {asset_id}")
        return self.repo.list_by_asset(asset_id)
