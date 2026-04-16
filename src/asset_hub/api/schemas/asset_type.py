from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class CustomFieldDef(BaseModel):
    key: str
    label: str
    type: str
    required: bool = False
    options: list[str] | None = None


class TypeCreate(BaseModel):
    name: str
    description: str | None = None
    custom_fields: list[CustomFieldDef] = []


class TypeRead(BaseModel):
    id: UUID
    name: str
    description: str | None
    custom_fields: list[CustomFieldDef]
    created_at: datetime
    updated_at: datetime
