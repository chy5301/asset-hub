import uuid
from datetime import UTC, datetime

from sqlalchemy import Index, text
from sqlmodel import Field, SQLModel


class CheckoutRecord(SQLModel, table=True):
    __tablename__ = "checkout_records"
    __table_args__ = (
        Index(
            "ix_one_open_checkout_per_asset",
            "asset_id",
            unique=True,
            sqlite_where=text("returned_at IS NULL"),
            postgresql_where=text("returned_at IS NULL"),
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    asset_id: uuid.UUID = Field(foreign_key="assets.id", index=True)
    holder: str
    location: str | None = None
    checked_out_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    returned_at: datetime | None = Field(default=None, index=True)
    checkout_note: str | None = None
    return_note: str | None = None
    return_location: str | None = None
    return_receiver: str | None = None
