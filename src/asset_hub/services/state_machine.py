"""状态机校验层 SoT（M3a 子 spec §2.6）。

TRANSITION_RULES 是合法 from/to + holder/location 必填规则的唯一来源。
service 层不写 if-block 双层防御（C1 闭环）。
"""
from typing import Literal, NamedTuple

from asset_hub.errors import IllegalTransitionError
from asset_hub.models.asset import AssetStatus
from asset_hub.models.state_transition import TransitionKind

HolderRule = Literal["required", "optional", "forced_null", "ignored"]
LocationRule = Literal["required", "optional", "forced_null"]


class TransitionRule(NamedTuple):
    valid_from: frozenset[AssetStatus]
    to_status: AssetStatus | None  # None = 同 from（RELOCATE/TRANSFER_HOLDER）
    holder_rule: HolderRule
    location_rule: LocationRule


_ALL_BUT_DISPOSED = frozenset({
    AssetStatus.IDLE,
    AssetStatus.IN_USE,
    AssetStatus.MAINTENANCE,
    AssetStatus.RETIRED,
})


TRANSITION_RULES: dict[TransitionKind, TransitionRule] = {
    TransitionKind.CHECKOUT_INTERNAL: TransitionRule(
        valid_from=frozenset({AssetStatus.IDLE}),
        to_status=AssetStatus.IN_USE,
        holder_rule="required",
        location_rule="optional",
    ),
    TransitionKind.CHECKOUT_EXTERNAL: TransitionRule(
        valid_from=frozenset({AssetStatus.IDLE}),
        to_status=AssetStatus.IN_USE,
        holder_rule="required",
        location_rule="optional",
    ),
    TransitionKind.RETURN: TransitionRule(
        valid_from=frozenset({AssetStatus.IN_USE}),
        to_status=AssetStatus.IDLE,
        holder_rule="optional",
        location_rule="optional",
    ),
    TransitionKind.SEND_TO_MAINTENANCE: TransitionRule(
        valid_from=frozenset({AssetStatus.IDLE}),
        to_status=AssetStatus.MAINTENANCE,
        holder_rule="optional",
        location_rule="optional",
    ),
    TransitionKind.RECOVER_FROM_MAINTENANCE: TransitionRule(
        valid_from=frozenset({AssetStatus.MAINTENANCE}),
        to_status=AssetStatus.IDLE,
        holder_rule="optional",
        location_rule="optional",
    ),
    TransitionKind.RETIRE: TransitionRule(
        valid_from=frozenset({AssetStatus.IDLE, AssetStatus.MAINTENANCE}),
        to_status=AssetStatus.RETIRED,
        holder_rule="optional",
        location_rule="optional",
    ),
    TransitionKind.REINSTATE: TransitionRule(
        valid_from=frozenset({AssetStatus.RETIRED}),
        to_status=AssetStatus.IDLE,
        holder_rule="optional",
        location_rule="optional",
    ),
    TransitionKind.DISPOSE: TransitionRule(
        valid_from=frozenset({AssetStatus.RETIRED, AssetStatus.MAINTENANCE}),
        to_status=AssetStatus.DISPOSED,
        holder_rule="forced_null",
        location_rule="forced_null",
    ),
    TransitionKind.RELOCATE: TransitionRule(
        valid_from=_ALL_BUT_DISPOSED,
        to_status=None,
        holder_rule="ignored",
        location_rule="required",
    ),
    TransitionKind.TRANSFER_HOLDER: TransitionRule(
        valid_from=_ALL_BUT_DISPOSED,
        to_status=None,
        holder_rule="required",
        location_rule="optional",
    ),
}


def validate_transition(
    current_status: AssetStatus,
    kind: TransitionKind,
    to_holder: str | None,
    to_location: str | None,
) -> AssetStatus:
    """返回 to_status；非法抛 IllegalTransitionError。"""
    rule = TRANSITION_RULES[kind]
    if current_status not in rule.valid_from:
        raise IllegalTransitionError(
            f"{kind.value} 不能从 {current_status.value} 出发"
        )
    if rule.holder_rule == "required" and not to_holder:
        raise IllegalTransitionError(f"{kind.value} 必须提供 to_holder")
    if rule.location_rule == "required" and not to_location:
        raise IllegalTransitionError(f"{kind.value} 必须提供 to_location")
    return rule.to_status if rule.to_status is not None else current_status
