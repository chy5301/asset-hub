import uuid

from sqlalchemy import select
from sqlmodel import Session

from asset_hub.models.state_transition import StateTransitionRecord, TransitionKind


class TransitionRepository:
    def __init__(self, session: Session):
        self.session = session

    def add(self, record: StateTransitionRecord) -> None:
        self.session.add(record)

    def list_by_asset(self, asset_id: uuid.UUID) -> list[StateTransitionRecord]:
        stmt = (
            select(StateTransitionRecord)
            .where(StateTransitionRecord.asset_id == asset_id)
            .order_by(StateTransitionRecord.created_at.desc())
        )
        return list(self.session.scalars(stmt))

    def find_open_checkout_id(self, asset_id: uuid.UUID) -> uuid.UUID | None:
        """找到该 asset 的最近一条未关闭 CHECKOUT_*（closes_transition_id 不指向它的 CHECKOUT）。

        简化：找最新的 kind=CHECKOUT_*，再确认无对应 RETURN 闭合。
        """
        # 最近的 CHECKOUT_*
        checkout_stmt = (
            select(StateTransitionRecord)
            .where(
                StateTransitionRecord.asset_id == asset_id,
                StateTransitionRecord.kind.in_(
                    [TransitionKind.CHECKOUT_INTERNAL, TransitionKind.CHECKOUT_EXTERNAL]
                ),
            )
            .order_by(StateTransitionRecord.created_at.desc())
            .limit(1)
        )
        latest_checkout = self.session.scalars(checkout_stmt).first()
        if latest_checkout is None:
            return None

        # 是否已被某条 RETURN 关闭
        return_stmt = select(StateTransitionRecord).where(
            StateTransitionRecord.closes_transition_id == latest_checkout.id
        )
        already_returned = self.session.scalars(return_stmt).first()
        if already_returned is not None:
            return None  # 已闭合，无 OPEN

        return latest_checkout.id
