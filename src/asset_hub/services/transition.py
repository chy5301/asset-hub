import uuid
from datetime import UTC, datetime

from sqlmodel import Session

from asset_hub.errors import IllegalTransitionError
from asset_hub.models.state_transition import StateTransitionRecord, TransitionKind
from asset_hub.repositories.state_transition import TransitionRepository
from asset_hub.services.asset import AssetService
from asset_hub.services.state_machine import TRANSITION_RULES, validate_transition


class TransitionService:
    def __init__(self, session: Session):
        self.session = session
        self.repo = TransitionRepository(session)
        self.asset_svc = AssetService(session)

    def record_transition(
        self,
        asset_id: uuid.UUID,
        kind: TransitionKind,
        *,
        to_holder: str | None = None,
        to_location: str | None = None,
        note: str | None = None,
        due_at: datetime | None = None,
    ) -> StateTransitionRecord:
        asset = self.asset_svc.get_asset(asset_id)

        to_status = validate_transition(asset.status, kind, to_holder, to_location)
        rule = TRANSITION_RULES[kind]

        # holder/location 规则套用
        if rule.holder_rule == "forced_null":
            to_holder_final = None
        elif rule.holder_rule == "ignored":
            to_holder_final = asset.holder
        else:
            to_holder_final = to_holder

        if rule.location_rule == "forced_null":
            to_location_final = None
        else:
            to_location_final = to_location

        # 闭合最近 OPEN CHECKOUT_*（仅 RETURN 用）
        closes_id = None
        if kind == TransitionKind.RETURN:
            closes_id = self.repo.find_open_checkout_id(asset_id)
            if closes_id is None:
                raise IllegalTransitionError(f"资产无未归还的派发记录: {asset_id}")

        record = StateTransitionRecord(
            asset_id=asset_id,
            kind=kind,
            from_status=asset.status,
            to_status=to_status,
            from_holder=asset.holder,
            to_holder=to_holder_final,
            from_location=asset.location,
            to_location=to_location_final,
            note=note,
            due_at=due_at
            if kind in (TransitionKind.CHECKOUT_INTERNAL, TransitionKind.CHECKOUT_EXTERNAL)
            else None,
            closes_transition_id=closes_id,
        )
        self.repo.add(record)

        # 更新 asset 字段
        asset.status = to_status
        asset.holder = to_holder_final
        if to_location_final is not None or rule.location_rule == "forced_null":
            asset.location = to_location_final
        asset.updated_at = datetime.now(UTC)

        self.session.commit()
        self.session.refresh(record)
        return record

    def list_transitions(self, asset_id: uuid.UUID) -> list[StateTransitionRecord]:
        self.asset_svc.get_asset(asset_id)  # 404 兜底
        return self.repo.list_by_asset(asset_id)
