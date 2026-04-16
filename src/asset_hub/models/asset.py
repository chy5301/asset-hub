import uuid
from datetime import UTC, datetime
from enum import Enum

from sqlalchemy import Column
from sqlalchemy.types import JSON
from sqlmodel import Field, SQLModel


class AssetStatus(str, Enum):
    IN_USE = "IN_USE"
    IDLE = "IDLE"
    MAINTENANCE = "MAINTENANCE"
    RETIRED = "RETIRED"


class Asset(SQLModel, table=True):
    __tablename__ = "assets"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    serial_number: str | None = Field(default=None, unique=True, index=True)
    name: str = Field(index=True)
    type_id: uuid.UUID = Field(foreign_key="asset_types.id", index=True)
    status: AssetStatus = Field(default=AssetStatus.IDLE)
    holder: str | None = None
    location: str | None = None
    notes: str | None = None
    custom_data: dict = Field(default_factory=dict, sa_column=Column(JSON, nullable=False))
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
