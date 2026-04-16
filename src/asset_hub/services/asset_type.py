import uuid

from sqlalchemy.exc import IntegrityError
from sqlmodel import Session

from asset_hub.api.schemas.asset_type import CustomFieldDef
from asset_hub.errors import DuplicateError, NotFoundError, ValidationError
from asset_hub.models.asset_type import AssetType
from asset_hub.repositories.asset_type import TypeRepository


class TypeService:
    def __init__(self, session: Session):
        self.session = session
        self.repo = TypeRepository(session)

    def create_type(
        self,
        name: str,
        description: str | None = None,
        custom_fields: list | None = None,
    ) -> AssetType:
        fields = custom_fields or []
        try:
            [CustomFieldDef.model_validate(f) for f in fields]
        except Exception as e:
            raise ValidationError(f"custom_fields 结构无效: {e}") from e

        asset_type = AssetType(
            name=name,
            description=description,
            custom_fields=fields,
        )
        try:
            self.repo.add(asset_type)
            self.session.commit()
        except IntegrityError:
            self.session.rollback()
            raise DuplicateError(f"类型名称已存在: {name}")
        self.session.refresh(asset_type)
        return asset_type

    def get_type(self, type_id: uuid.UUID) -> AssetType:
        t = self.repo.get(type_id)
        if t is None:
            raise NotFoundError(f"类型不存在: {type_id}")
        return t

    def list_types(self) -> list[AssetType]:
        return self.repo.list_all()
