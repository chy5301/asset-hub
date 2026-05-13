import uuid
from datetime import UTC, datetime

from sqlalchemy import Column
from sqlalchemy.types import JSON
from sqlmodel import Field, SQLModel


class AssetType(SQLModel, table=True):
    __tablename__ = "asset_types"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str = Field(unique=True, index=True)
    code_prefix: str = Field(
        unique=True, index=True
    )  # 新；^[A-Z]{2,4}$；service 层 enforce 格式
    description: str | None = None
    custom_fields: list = Field(
        default_factory=list, sa_column=Column(JSON, nullable=False)
    )
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
