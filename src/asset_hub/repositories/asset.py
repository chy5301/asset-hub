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
        include_retired: bool = False,
        include_disposed: bool = False,
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
        # 默认按 asset_code 升序
        stmt = stmt.order_by(Asset.asset_code.asc())
        return list(self.session.exec(stmt).all())
