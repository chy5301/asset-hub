import uuid

from sqlmodel import Session, select

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
