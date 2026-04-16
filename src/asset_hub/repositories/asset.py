import uuid

from sqlmodel import Session, select

from asset_hub.models.asset import Asset, AssetStatus


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
    ) -> list[Asset]:
        stmt = select(Asset)
        if type_id is not None:
            stmt = stmt.where(Asset.type_id == type_id)
        if status is not None:
            stmt = stmt.where(Asset.status == status)
        if holder is not None:
            stmt = stmt.where(Asset.holder == holder)
        if q is not None:
            stmt = stmt.where(
                Asset.name.contains(q)
                | Asset.serial_number.contains(q)
                | Asset.notes.contains(q)
            )
        return list(self.session.exec(stmt).all())
