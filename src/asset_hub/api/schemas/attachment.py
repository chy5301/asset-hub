from uuid import UUID

from pydantic import BaseModel, ConfigDict

from asset_hub.api.schemas._datetime import UtcDatetime
from asset_hub.models.attachment import AttachmentKind


class AttachmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    asset_id: UUID
    kind: AttachmentKind
    sha256: str
    size: int
    mime_type: str
    original_name: str
    uploaded_at: UtcDatetime
