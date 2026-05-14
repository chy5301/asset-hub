import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from asset_hub.api.schemas._datetime import UtcDatetime
from asset_hub.models.asset import AssetStatus
from asset_hub.models.state_transition import TransitionKind


class TransitionCreate(BaseModel):
    kind: TransitionKind
    to_holder: str | None = None
    to_location: str | None = None
    note: str | None = None
    # request 入参：客户端传带 tz 的 ISO；不应用 UtcDatetime
    # （避免把客户端显式 naive datetime 误判成 UTC）
    due_at: datetime | None = None


class TransitionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    asset_id: uuid.UUID
    kind: TransitionKind
    from_status: AssetStatus
    to_status: AssetStatus
    from_holder: str | None
    to_holder: str | None
    from_location: str | None
    to_location: str | None
    note: str | None
    due_at: UtcDatetime | None
    closes_transition_id: uuid.UUID | None
    created_at: UtcDatetime
