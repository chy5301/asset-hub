"""状态机校验层 SoT（v2.0 spec §2.4）。

TRANSITION_RULES 是合法 from/to + holder/location 规则的唯一来源。
service 层不写 if-block 双层防御。
"""
from typing import Literal, NamedTuple

from asset_hub.errors import IllegalTransitionError
from asset_hub.models.asset import AssetStatus
from asset_hub.models.state_transition import TransitionKind

HolderRule = Literal["required", "optional", "forced_null", "ignored", "keep"]
LocationRule = Literal["required", "optional", "forced_null", "keep"]


class TransitionRule(NamedTuple):
    valid_from: frozenset[AssetStatus]
    to_status: AssetStatus | None  # None = self-loop（REASSIGN）
    holder_rule: HolderRule
    location_rule: LocationRule


_ALL_BUT_DISPOSED = frozenset({
    AssetStatus.IDLE,
    AssetStatus.IN_USE,
    AssetStatus.MAINTENANCE,
    AssetStatus.BROKEN,
    AssetStatus.RETIRED,
})


# 派出延续状态集合（v2.0 新引入）
# closes 通用化检测：from ∈ 派出集 且 to ∉ 派出集 → 自动 closes 最近 OPEN CHECKOUT
PERSISTED_CHECKOUT_STATES = frozenset({AssetStatus.IN_USE, AssetStatus.BROKEN})


TRANSITION_RULES: dict[TransitionKind, TransitionRule] = {
    TransitionKind.CHECKOUT_INTERNAL: TransitionRule(
        valid_from=frozenset({AssetStatus.IDLE}),
        to_status=AssetStatus.IN_USE,
        holder_rule="required",
        location_rule="keep",
    ),
    TransitionKind.CHECKOUT_EXTERNAL: TransitionRule(
        valid_from=frozenset({AssetStatus.IDLE}),
        to_status=AssetStatus.IN_USE,
        holder_rule="required",
        location_rule="keep",
    ),
    TransitionKind.RETURN: TransitionRule(
        valid_from=frozenset({AssetStatus.IN_USE}),
        to_status=AssetStatus.IDLE,
        holder_rule="optional",
        location_rule="keep",
    ),
    TransitionKind.SEND_TO_MAINTENANCE: TransitionRule(
        valid_from=frozenset({AssetStatus.IDLE, AssetStatus.BROKEN}),
        to_status=AssetStatus.MAINTENANCE,
        holder_rule="keep",
        location_rule="keep",
    ),
    TransitionKind.RECOVER_FROM_MAINTENANCE: TransitionRule(
        valid_from=frozenset({AssetStatus.MAINTENANCE}),
        to_status=AssetStatus.IDLE,
        holder_rule="keep",
        location_rule="keep",
    ),
    TransitionKind.RETIRE: TransitionRule(
        valid_from=frozenset({AssetStatus.IDLE, AssetStatus.MAINTENANCE, AssetStatus.BROKEN}),
        to_status=AssetStatus.RETIRED,
        holder_rule="keep",
        location_rule="keep",
    ),
    TransitionKind.REINSTATE: TransitionRule(
        valid_from=frozenset({AssetStatus.RETIRED}),
        to_status=AssetStatus.IDLE,
        holder_rule="keep",
        location_rule="keep",
    ),
    TransitionKind.DISPOSE: TransitionRule(
        valid_from=frozenset({AssetStatus.RETIRED, AssetStatus.MAINTENANCE, AssetStatus.BROKEN}),
        to_status=AssetStatus.DISPOSED,
        holder_rule="forced_null",
        location_rule="forced_null",
    ),
    TransitionKind.REASSIGN: TransitionRule(
        valid_from=_ALL_BUT_DISPOSED,
        to_status=None,
        holder_rule="keep",
        location_rule="keep",
    ),
    TransitionKind.REPORT_BROKEN: TransitionRule(
        valid_from=frozenset({AssetStatus.IDLE, AssetStatus.IN_USE}),
        to_status=AssetStatus.BROKEN,
        holder_rule="keep",
        location_rule="keep",
    ),
    TransitionKind.DECLARE_UNREPAIRABLE: TransitionRule(
        valid_from=frozenset({AssetStatus.MAINTENANCE}),
        to_status=AssetStatus.BROKEN,
        holder_rule="keep",
        location_rule="keep",
    ),
    TransitionKind.DISMISS: TransitionRule(
        valid_from=frozenset({AssetStatus.BROKEN}),
        to_status=AssetStatus.IDLE,
        holder_rule="keep",
        location_rule="keep",
    ),
}


def validate_transition(
    current_status: AssetStatus,
    kind: TransitionKind,
    to_holder: str | None,
    to_location: str | None,
) -> AssetStatus | None:
    """返回 to_status；非法抛 IllegalTransitionError。

    注：v2.0 中 to_holder/to_location 在 keep rule 下由 service 层（transition.py）
    决定是否清空/保留——此函数只校验 required 规则。"keep" rule 不要求字段，但若
    显式传 None 表示清空（service 层会区分 UNSET 哨兵 vs None）。
    """
    rule = TRANSITION_RULES[kind]
    if current_status not in rule.valid_from:
        raise IllegalTransitionError(
            f"{kind.value} 不能从 {current_status.value} 出发"
        )
    if rule.holder_rule == "required" and not to_holder:
        raise IllegalTransitionError(f"{kind.value} 必须提供 to_holder")
    if rule.location_rule == "required" and not to_location:
        raise IllegalTransitionError(f"{kind.value} 必须提供 to_location")
    return rule.to_status  # 注意：REASSIGN self-loop 时返回 None，由 service 层处理
