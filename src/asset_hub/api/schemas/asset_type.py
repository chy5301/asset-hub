from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator


class CustomFieldDef(BaseModel):
    """v1 schema：key + label + type + required + options + 扩展属性。

    M2c-3 D2 决议：字段名沿用 M1/M2 的 `key`（与 services/validation.py:8 + 现有 fixtures 一致），
    不重命名为 name；spec D2 文案随 plan Task 15 同步使用 `key`（前端 FieldDef 也用 key）。
    """
    key: str
    label: str | None = None
    type: str
    required: bool = False
    default: str | int | float | bool | None = None
    placeholder: str | None = None
    help: str | None = None
    unit: str | None = None
    min: float | None = None
    max: float | None = None
    options: list[str] | None = None
    displayAs: str | None = None  # 'radio' | 'select'
    # 注意：不需要 model_config / Field(alias=...) —— key 就是字段本名


class TypeCreate(BaseModel):
    name: str
    code_prefix: str  # 新；必填；^[A-Z]{2,4}$ 由 service 校验
    description: str | None = None
    custom_fields: list[CustomFieldDef] = []

    @field_validator("code_prefix", mode="before")
    @classmethod
    def normalize_prefix(cls, v):
        if isinstance(v, str):
            return v.upper().strip()
        return v


class TypeUpdate(BaseModel):
    """注意：code_prefix immutable，update DTO 不暴露此字段（D5）。"""
    name: str | None = None
    description: str | None = None
    custom_fields: list[CustomFieldDef] | None = None


class TypeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    code_prefix: str  # 新
    description: str | None
    custom_fields: list[CustomFieldDef]
    ref_count: int = 0
    created_at: datetime
    updated_at: datetime
