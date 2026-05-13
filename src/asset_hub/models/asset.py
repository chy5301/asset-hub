import uuid
from datetime import UTC, date, datetime
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import Column
from sqlalchemy.types import JSON
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from asset_hub.models.asset_type import AssetType


class AssetStatus(StrEnum):
    IDLE = "IDLE"
    IN_USE = "IN_USE"
    MAINTENANCE = "MAINTENANCE"
    BROKEN = "BROKEN"
    RETIRED = "RETIRED"
    DISPOSED = "DISPOSED"


class Asset(SQLModel, table=True):
    __tablename__ = "assets"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    asset_code: str = Field(
        unique=True, index=True
    )  # 新；{prefix}-{seq:03d}，service 层生成
    serial_number: str | None = Field(default=None, unique=True, index=True)
    name: str = Field(index=True)
    model: str | None = Field(
        default=None, index=True
    )  # nullable / non-unique; index 与 name 对齐
    type_id: uuid.UUID = Field(foreign_key="asset_types.id", index=True)
    status: AssetStatus = Field(default=AssetStatus.IDLE)
    holder: str | None = None
    location: str | None = None
    notes: str | None = None
    custom_data: dict = Field(
        default_factory=dict, sa_column=Column(JSON, nullable=False)
    )
    acquired_at: date | None = Field(default=None)  # 新；业务入账日期
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    # type_name 反规范化（plan 决议：SQLModel Relationship + lazy="joined" + Asset.type_name @property）
    asset_type: "AssetType" = Relationship(sa_relationship_kwargs={"lazy": "joined"})

    @property
    def type_name(self) -> str | None:
        """Pydantic AssetRead 通过 from_attributes 自动读取此 property。

        N+1 防护：Relationship 的 lazy="joined" 兜底，对单一 asset query 无 N+1 风险；
        list_assets 走 select(Asset) 时也会自动 JOIN。
        """
        return self.asset_type.name if self.asset_type else None

    @property
    def idle_days(self) -> int | None:
        """非 IDLE 状态返 None；IDLE 状态由 service 层 annotate_idle_days() 注入实例属性 _idle_days_value。
        惰性计算——通过 service 单独查询 StateTransitionRecord，避免 ORM 层访问 session。
        """
        return getattr(self, "_idle_days_value", None)
