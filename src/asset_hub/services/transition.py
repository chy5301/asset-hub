import uuid
from datetime import UTC, datetime
from typing import Final

from sqlmodel import Session

from asset_hub.errors import IllegalTransitionError
from asset_hub.models.state_transition import StateTransitionRecord, TransitionKind
from asset_hub.repositories.state_transition import TransitionRepository
from asset_hub.services.asset import AssetService
from asset_hub.services.state_machine import (
    PERSISTED_CHECKOUT_STATES,
    TRANSITION_RULES,
    validate_transition,
)


class _UnsetType:
    """部分更新哨兵——区分'未传字段'与'显式传 None（清空）'。"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __repr__(self) -> str:
        return "_UNSET"

    def __bool__(self) -> bool:
        return False


_UNSET: Final = _UnsetType()


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
        to_holder: str | None | _UnsetType = _UNSET,
        to_location: str | None | _UnsetType = _UNSET,
        note: str | None = None,
        due_at: datetime | None = None,
    ) -> StateTransitionRecord:
        asset = self.asset_svc.get_asset(asset_id)

        # validate_transition 接受 None（视为'未传'）；_UNSET 哨兵映射到 None
        _check_holder = None if isinstance(to_holder, _UnsetType) else to_holder
        _check_location = None if isinstance(to_location, _UnsetType) else to_location
        to_status = validate_transition(asset.status, kind, _check_holder, _check_location)
        rule = TRANSITION_RULES[kind]

        # REASSIGN 必改一项校验：to_holder 或 to_location 至少一项有变化
        if kind == TransitionKind.REASSIGN:
            holder_changed = not isinstance(to_holder, _UnsetType) and to_holder != asset.holder
            location_changed = not isinstance(to_location, _UnsetType) and to_location != asset.location
            if not holder_changed and not location_changed:
                raise IllegalTransitionError(
                    "REASSIGN 必须改 holder 或 location 至少一项"
                )

        # to_status 可能为 None（REASSIGN self-loop），fallback 到 asset.status
        new_status = to_status if to_status is not None else asset.status

        # holder 规则套用
        if rule.holder_rule == "forced_null":
            to_holder_final = None
        elif rule.holder_rule == "ignored":
            to_holder_final = asset.holder
        elif rule.holder_rule == "keep":
            to_holder_final = asset.holder if isinstance(to_holder, _UnsetType) else to_holder
        else:  # required / optional
            to_holder_final = None if isinstance(to_holder, _UnsetType) else to_holder

        # location 规则套用
        if rule.location_rule == "forced_null":
            to_location_final = None
        elif rule.location_rule == "keep":
            to_location_final = asset.location if isinstance(to_location, _UnsetType) else to_location
        else:  # required / optional
            to_location_final = None if isinstance(to_location, _UnsetType) else to_location

        # 派出集 closes 通用化（v2.0）
        # 关键：用 new_status 而非 to_status 判断（处理 REASSIGN.to_status=None self-loop）
        closes_id = None
        if (asset.status in PERSISTED_CHECKOUT_STATES
                and new_status not in PERSISTED_CHECKOUT_STATES):
            closes_id = self.repo.find_open_checkout_id(asset_id)
            # RETURN 强约束：必须有 OPEN CHECKOUT（v1.0 行为保留）
            if kind == TransitionKind.RETURN and closes_id is None:
                raise IllegalTransitionError(f"资产无未归还的派发记录: {asset_id}")
            # 其他从派出集走出的 transition：closes_id 为 None 也合法

        record = StateTransitionRecord(
            asset_id=asset_id,
            kind=kind,
            from_status=asset.status,
            to_status=new_status,
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
        asset.status = new_status
        asset.holder = to_holder_final
        asset.location = to_location_final
        asset.updated_at = datetime.now(UTC)

        self.session.commit()
        self.session.refresh(record)
        return record

    def list_transitions(self, asset_id: uuid.UUID) -> list[StateTransitionRecord]:
        self.asset_svc.get_asset(asset_id)  # 404 兜底
        return self.repo.list_by_asset(asset_id)
