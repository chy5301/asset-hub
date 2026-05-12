import uuid
from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy import Index
from sqlmodel import Field, SQLModel

from asset_hub.models.asset import AssetStatus


class TransitionKind(StrEnum):
    CHECKOUT_INTERNAL = "CHECKOUT_INTERNAL"
    CHECKOUT_EXTERNAL = "CHECKOUT_EXTERNAL"
    RETURN = "RETURN"
    SEND_TO_MAINTENANCE = "SEND_TO_MAINTENANCE"
    RECOVER_FROM_MAINTENANCE = "RECOVER_FROM_MAINTENANCE"
    RETIRE = "RETIRE"
    REINSTATE = "REINSTATE"
    DISPOSE = "DISPOSE"
    REASSIGN = "REASSIGN"                              # v2.0 新（合并 RELOCATE + TRANSFER_HOLDER）
    REPORT_BROKEN = "REPORT_BROKEN"                    # v2.0 新
    DECLARE_UNREPAIRABLE = "DECLARE_UNREPAIRABLE"      # v2.0 新
    DISMISS = "DISMISS"                                # v2.0 新


class StateTransitionRecord(SQLModel, table=True):
    __tablename__ = "state_transition_records"
    __table_args__ = (
        Index("ix_transition_asset_created", "asset_id", "created_at"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    asset_id: uuid.UUID = Field(foreign_key="assets.id", index=True)
    kind: TransitionKind
    from_status: AssetStatus
    to_status: AssetStatus
    from_holder: str | None = None
    to_holder: str | None = None
    from_location: str | None = None
    to_location: str | None = None
    note: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC), index=True)
    due_at: datetime | None = None
    closes_transition_id: uuid.UUID | None = Field(
        default=None,
        foreign_key="state_transition_records.id",
        index=True,
    )
