from datetime import date, datetime
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
    acquired_at: date | None = None  # 新

    # 注意：asset_code 不在 Create body 中——系统自动生成


class AssetUpdate(BaseModel):
    """注意：
    - type_id 不暴露——D9 编辑表单禁改 type；
    - asset_code 不暴露——系统生成、不允许手改；
    - status/holder/location 不暴露——M3a 后必须走 POST /api/assets/{id}/transitions，经 state machine 校验。
    """

    name: str | None = None
    serial_number: str | None = None
    notes: str | None = None
    custom_data: dict | None = None
    acquired_at: date | None = None  # 新


class AssetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    asset_code: str  # 新
    name: str
    serial_number: str | None
    type_id: UUID
    type_name: str | None  # 新；从 Asset.type_name @property 自动读取
    status: AssetStatus
    holder: str | None
    location: str | None
    notes: str | None
    custom_data: dict
    acquired_at: date | None  # 新
    created_at: datetime
    updated_at: datetime
