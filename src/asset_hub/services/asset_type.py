import re
import uuid
from datetime import UTC, datetime

from sqlalchemy.exc import IntegrityError
from sqlmodel import Session

from asset_hub.api.schemas.asset_type import CustomFieldDef, TypeRead
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

    def _validate_and_dump_fields(self, fields: list) -> list[dict]:
        try:
            return [CustomFieldDef.model_validate(f).model_dump() for f in fields]
        except Exception as e:
            raise ValidationError(f"custom_fields 结构无效: {e}") from e

    def _to_read(self, t: AssetType, ref_count: int = 0) -> TypeRead:
        return TypeRead.model_validate(t).model_copy(update={"ref_count": ref_count})

    def count_refs(self, type_id: uuid.UUID) -> int:
        return self.repo.count_assets_by_type(type_id)

    def create_type(
        self,
        name: str,
        code_prefix: str,
        description: str | None = None,
        custom_fields: list | None = None,
    ) -> TypeRead:
        normalized_prefix = (code_prefix or "").upper().strip()
        if not _PREFIX_RE.fullmatch(normalized_prefix):
            raise ValidationError(
                f"code_prefix 格式不合法：'{code_prefix}'，需要 2-4 个大写字母（^[A-Z]{{2,4}}$）"
            )

        validated_fields = self._validate_and_dump_fields(custom_fields or [])

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
        return self._to_read(asset_type, ref_count=0)

    def get_type(self, type_id: uuid.UUID) -> TypeRead:
        t = self._get_orm(type_id)
        return self._to_read(t, ref_count=self.count_refs(type_id))

    def _get_orm(self, type_id: uuid.UUID) -> AssetType:
        t = self.repo.get(type_id)
        if t is None:
            raise NotFoundError(f"类型不存在: {type_id}")
        return t

    def list_types(self) -> list[TypeRead]:
        types = self.repo.list_all()
        counts = self.repo.count_assets_grouped_by_type()
        return [self._to_read(t, ref_count=counts.get(t.id, 0)) for t in types]

    def delete_type(self, type_id: uuid.UUID) -> None:
        t = self._get_orm(type_id)  # 不存在抛 NotFoundError
        ref_count = self.count_refs(type_id)
        if ref_count > 0:
            raise ConflictError(
                f"该类型仍有 {ref_count} 个资产引用，请先删除/迁移所有引用此类型的资产"
            )
        self.repo.delete(t)
        self.session.commit()

    def update_type(
        self,
        type_id: uuid.UUID,
        name: str | None = None,
        description: str | None = None,
        custom_fields: list | None = None,
    ) -> TypeRead:
        """部分更新 type。code_prefix immutable，故签名不接收。

        参数为 None 表示"未传"，对应字段不动；显式传值才更新。
        custom_fields 传入时按 CustomFieldDef 校验后**完全替换**（非 merge）。

        v1 设计取舍：本方法不采用 ``AssetService.update_asset`` 的 ``_Unset`` 哨兵
        模式（CLAUDE.md §5）。``description=None`` 视为"未传"而非"清空为 NULL"。
        清空 description 请传 ``""``。理由见 spec §4.2（M2c-4 design doc）：
        v1 不区分 null/未传，前端按需。
        """
        t = self._get_orm(type_id)  # 不存在抛 NotFoundError

        changed = False
        if name is not None and name != t.name:
            t.name = name
            changed = True
        if description is not None and description != t.description:
            t.description = description
            changed = True
        if custom_fields is not None:
            new_cf = self._validate_and_dump_fields(custom_fields)
            if new_cf != t.custom_fields:
                t.custom_fields = new_cf
                changed = True

        if not changed:
            return self._to_read(t, ref_count=self.count_refs(type_id))  # 跳 commit 避免 updated_at 漂移

        t.updated_at = datetime.now(UTC)
        try:
            self.session.commit()
        except IntegrityError:
            self.session.rollback()
            raise DuplicateError(f"类型名称已存在: {name}") from None
        # 必需：caller 持 session context，commit 后 expire
        self.session.refresh(t)
        # count_refs 在 commit 后调用避免 autoflush 把 dirty t 提前推送（触发 UNIQUE 冲突误报）
        return self._to_read(t, ref_count=self.count_refs(type_id))
