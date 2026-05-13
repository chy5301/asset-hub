import uuid
from datetime import UTC, datetime

from sqlmodel import Session

from asset_hub.errors import IllegalTransitionError
from asset_hub.models.state_transition import StateTransitionRecord, TransitionKind
from asset_hub.repositories.state_transition import TransitionRepository
from asset_hub.services._common import UNSET, UnsetType
from asset_hub.services.asset import AssetService
from asset_hub.services.state_machine import (
    PERSISTED_CHECKOUT_STATES,
    TRANSITION_RULES,
    HolderRule,
    LocationRule,
    validate_transition,
)


def _apply_holder_rule(
    rule_kind: HolderRule,
    current: str | None,
    incoming: str | None | UnsetType,
) -> str | None:
    """根据 holder_rule 决定最终 holder 字段值。

    forced_null  → None（强制清空，无视输入）
    ignored      → current（保留当前，无视输入；v1 残留 rule，v2 无使用）
    keep         → current if UNSET else incoming（哨兵 → 保留；显式值/None → 用输入）
    required/optional → None if UNSET else incoming（哨兵 → None；显式值 → 用输入）
    """
    if rule_kind == "forced_null":
        return None
    if rule_kind == "ignored":
        return current
    if rule_kind == "keep":
        return current if isinstance(incoming, UnsetType) else incoming
    # required / optional
    return None if isinstance(incoming, UnsetType) else incoming


def _apply_location_rule(
    rule_kind: LocationRule,
    current: str | None,
    incoming: str | None | UnsetType,
) -> str | None:
    """根据 location_rule 决定最终 location 字段值。

    forced_null → None
    keep        → current if UNSET else incoming
    required/optional → None if UNSET else incoming
    """
    if rule_kind == "forced_null":
        return None
    if rule_kind == "keep":
        return current if isinstance(incoming, UnsetType) else incoming
    # required / optional
    return None if isinstance(incoming, UnsetType) else incoming


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
        to_holder: str | None | UnsetType = UNSET,
        to_location: str | None | UnsetType = UNSET,
        note: str | None = None,
        due_at: datetime | None = None,
    ) -> StateTransitionRecord:
        asset = self.asset_svc.get_asset(asset_id)

        # validate_transition 接受 None（视为'未传'）；UNSET 哨兵映射到 None
        _check_holder = None if isinstance(to_holder, UnsetType) else to_holder
        _check_location = None if isinstance(to_location, UnsetType) else to_location
        to_status = validate_transition(asset.status, kind, _check_holder, _check_location)
        rule = TRANSITION_RULES[kind]

        # REASSIGN 必改一项校验：to_holder 或 to_location 至少一项有变化
        if kind == TransitionKind.REASSIGN:
            holder_changed = not isinstance(to_holder, UnsetType) and to_holder != asset.holder
            location_changed = not isinstance(to_location, UnsetType) and to_location != asset.location
            if not holder_changed and not location_changed:
                raise IllegalTransitionError(
                    "REASSIGN 必须改 holder 或 location 至少一项",
                    hint="传入 to_holder 或 to_location 至少一项（CLI: --to-holder / --to-location）",
                    fields_missing=["to_holder", "to_location"],
                )

        # to_status 可能为 None（REASSIGN self-loop），fallback 到 asset.status
        new_status = to_status if to_status is not None else asset.status

        # holder / location 规则套用（抽取为纯函数）
        to_holder_final = _apply_holder_rule(rule.holder_rule, asset.holder, to_holder)
        to_location_final = _apply_location_rule(rule.location_rule, asset.location, to_location)

        # 派出集 closes 通用化（v2.0）
        # 关键：用 new_status 而非 to_status 判断（处理 REASSIGN.to_status=None self-loop）
        closes_id = None
        if (asset.status in PERSISTED_CHECKOUT_STATES
                and new_status not in PERSISTED_CHECKOUT_STATES):
            closes_id = self.repo.find_open_checkout_id(asset_id)
            # RETURN 强约束：必须有 OPEN CHECKOUT（v1.0 行为保留）
            if kind == TransitionKind.RETURN and closes_id is None:
                raise IllegalTransitionError(
                    f"资产无未归还的派发记录: {asset_id}",
                    hint="此资产当前不在 IN_USE 状态，无 OPEN CHECKOUT 可关闭。先用 asset show 检查当前 status。",
                    affected_resource_id=str(asset_id),
                )
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
