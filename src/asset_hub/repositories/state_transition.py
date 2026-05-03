import uuid

from sqlmodel import Session, select

from asset_hub.models.state_transition import StateTransitionRecord, TransitionKind


class TransitionRepository:
    def __init__(self, session: Session):
        self.session = session

    def add(self, record: StateTransitionRecord) -> StateTransitionRecord:
        self.session.add(record)
        self.session.flush()
        return record

    def list_by_asset(self, asset_id: uuid.UUID) -> list[StateTransitionRecord]:
        """按 created_at 倒序返回（newest-first）。"""
        stmt = (
            select(StateTransitionRecord)
            .where(StateTransitionRecord.asset_id == asset_id)
            .order_by(StateTransitionRecord.created_at.desc())
        )
        return list(self.session.exec(stmt).all())

    def find_open_checkout_id(self, asset_id: uuid.UUID) -> uuid.UUID | None:
        """找到该 asset 最近一条未关闭 CHECKOUT_*。

        简化：选最新的 kind ∈ (CHECKOUT_INTERNAL, CHECKOUT_EXTERNAL)，
        再确认无对应 RETURN（closes_transition_id 指向它）。
        """
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
        latest_checkout = self.session.exec(checkout_stmt).first()
        if latest_checkout is None:
            return None

        return_stmt = select(StateTransitionRecord).where(
            StateTransitionRecord.closes_transition_id == latest_checkout.id
        )
        already_returned = self.session.exec(return_stmt).first()
        if already_returned is not None:
            return None

        return latest_checkout.id
