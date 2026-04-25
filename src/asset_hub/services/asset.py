import uuid
from datetime import UTC, datetime

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
    ) -> Asset:
        asset_type = self.type_repo.get(type_id)
        if asset_type is None:
            raise NotFoundError(f"类型不存在: {type_id}")

        validated_data = validate_custom_data(asset_type.custom_fields, custom_data)

        asset = Asset(
            name=name,
            type_id=type_id,
            serial_number=serial_number,
            holder=holder,
            location=location,
            notes=notes,
            custom_data=validated_data,
        )
        try:
            self.repo.add(asset)
            self.session.commit()
        except IntegrityError:
            self.session.rollback()
            raise DuplicateError(f"序列号重复: {serial_number}") from None
        self.session.refresh(asset)
        return asset

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
    ) -> Asset:
        a = self.get_asset(asset_id)
        if name is not None:
            a.name = name
        if not isinstance(serial_number, _Unset):
            a.serial_number = serial_number
        if status is not None:
            a.status = status
        if not isinstance(holder, _Unset):
            a.holder = holder
        if not isinstance(location, _Unset):
            a.location = location
        if not isinstance(notes, _Unset):
            a.notes = notes
        a.updated_at = datetime.now(UTC)
        self.session.commit()
        self.session.refresh(a)
        return a

    def delete_asset(self, asset_id: uuid.UUID) -> None:
        a = self.get_asset(asset_id)
        self.repo.delete(a)
        self.session.commit()
