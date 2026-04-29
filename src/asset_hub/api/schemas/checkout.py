from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class CheckoutCreate(BaseModel):
    holder: str
    location: str | None = None
    note: str | None = None


class CheckoutReturn(BaseModel):
    note: str | None = None
    return_location: str | None = None
    return_receiver: str | None = None


class CheckoutRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    asset_id: UUID
    holder: str
    location: str | None
    checked_out_at: datetime
    returned_at: datetime | None
    checkout_note: str | None
    return_note: str | None
    return_location: str | None
    return_receiver: str | None
