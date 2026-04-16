from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from asset_hub.models.asset import AssetStatus


class AssetCreate(BaseModel):
    name: str
    type_id: UUID
    serial_number: str | None = None
    holder: str | None = None
    location: str | None = None
    notes: str | None = None
    custom_data: dict = Field(default_factory=dict)


class AssetUpdate(BaseModel):
    name: str | None = None
    serial_number: str | None = None
    status: AssetStatus | None = None
    holder: str | None = None
    location: str | None = None
    notes: str | None = None


class AssetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    serial_number: str | None
    type_id: UUID
    status: AssetStatus
    holder: str | None
    location: str | None
    notes: str | None
    custom_data: dict
    created_at: datetime
    updated_at: datetime
