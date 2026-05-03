import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from asset_hub.models.asset import AssetStatus
from asset_hub.models.state_transition import TransitionKind


class TransitionCreate(BaseModel):
    kind: TransitionKind
    to_holder: str | None = None
    to_location: str | None = None
    note: str | None = None
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
    due_at: datetime | None
    closes_transition_id: uuid.UUID | None
    created_at: datetime
