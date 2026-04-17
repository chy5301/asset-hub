import uuid
from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel


class AttachmentKind(StrEnum):
    PHOTO = "photo"
    INVOICE = "invoice"
    DOC = "doc"
    OTHER = "other"


class Attachment(SQLModel, table=True):
    __tablename__ = "attachments"
    __table_args__ = (
        UniqueConstraint("asset_id", "sha256", name="uq_attachment_asset_sha256"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    asset_id: uuid.UUID = Field(foreign_key="assets.id", index=True)
    kind: AttachmentKind = Field(default=AttachmentKind.OTHER)
    storage_path: str  # 相对 storage root 的路径，如 "2026/04/<sha256>.jpg"
    sha256: str = Field(index=True)
    size: int
    mime_type: str
    original_name: str
    uploaded_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
