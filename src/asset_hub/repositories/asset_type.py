import uuid

from sqlalchemy import func
from sqlmodel import Session, select

from asset_hub.models.asset import Asset
from asset_hub.models.asset_type import AssetType


class TypeRepository:
    def __init__(self, session: Session):
        self.session = session

    def add(self, asset_type: AssetType) -> AssetType:
        self.session.add(asset_type)
        self.session.flush()
        return asset_type

    def get(self, type_id: uuid.UUID) -> AssetType | None:
        return self.session.get(AssetType, type_id)

    def list_all(self) -> list[AssetType]:
        return list(self.session.exec(select(AssetType)).all())

    def count_assets_by_type(self, type_id: uuid.UUID) -> int:
        stmt = select(func.count()).select_from(Asset).where(Asset.type_id == type_id)
        return self.session.exec(stmt).one()

    def count_assets_grouped_by_type(self) -> dict[uuid.UUID, int]:
        stmt = select(Asset.type_id, func.count()).group_by(Asset.type_id)
        return {tid: c for tid, c in self.session.exec(stmt).all()}

    def delete(self, asset_type: AssetType) -> None:
        self.session.delete(asset_type)
