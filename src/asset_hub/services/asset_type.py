import re
import uuid

from sqlalchemy.exc import IntegrityError
from sqlmodel import Session

from asset_hub.api.schemas.asset_type import CustomFieldDef
from asset_hub.errors import (
    ConflictError,
    DuplicateError,
    NotFoundError,
    ValidationError,
)
from asset_hub.models.asset_type import AssetType
from asset_hub.repositories.asset_type import TypeRepository

_PREFIX_RE = re.compile(r"^[A-Z]{2,4}$")


class TypeService:
    def __init__(self, session: Session):
        self.session = session
        self.repo = TypeRepository(session)

    def create_type(
        self,
        name: str,
        code_prefix: str,
        description: str | None = None,
        custom_fields: list | None = None,
    ) -> AssetType:
        normalized_prefix = (code_prefix or "").upper().strip()
        if not _PREFIX_RE.fullmatch(normalized_prefix):
            raise ValidationError(
                f"code_prefix 格式不合法：'{code_prefix}'，需要 2-4 个大写字母（^[A-Z]{{2,4}}$）"
            )

        fields = custom_fields or []
        try:
            validated_fields = [CustomFieldDef.model_validate(f).model_dump() for f in fields]
        except Exception as e:
            raise ValidationError(f"custom_fields 结构无效: {e}") from e

        asset_type = AssetType(
            name=name,
            code_prefix=normalized_prefix,
            description=description,
            custom_fields=validated_fields,
        )
        try:
            self.repo.add(asset_type)
            self.session.commit()
        except IntegrityError as e:
            self.session.rollback()
            msg = str(e).lower()
            if "code_prefix" in msg:
                raise DuplicateError(f"code_prefix 已存在: {normalized_prefix}") from None
            raise DuplicateError(f"类型名称已存在: {name}") from None
        self.session.refresh(asset_type)
        return asset_type

    def get_type(self, type_id: uuid.UUID) -> AssetType:
        t = self.repo.get(type_id)
        if t is None:
            raise NotFoundError(f"类型不存在: {type_id}")
        return t

    def list_types(self) -> list[AssetType]:
        return self.repo.list_all()

    def delete_type(self, type_id: uuid.UUID) -> None:
        t = self.get_type(type_id)  # 不存在抛 NotFoundError
        ref_count = self.repo.count_assets_by_type(type_id)
        if ref_count > 0:
            raise ConflictError(
                f"该类型仍有 {ref_count} 个资产引用，请先删除/迁移所有引用此类型的资产"
            )
        self.repo.delete(t)
        self.session.commit()
