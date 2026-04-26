"""资产状态转换合法性矩阵（M2c-3 spec §5.5 / D14）。

简化路径：
- MAINTENANCE 仅从 IDLE 进入
- RETIRED 仅从 IDLE / MAINTENANCE 进入
- IN_USE 状态下要任何状态切换必须先归还
- RETIRED 唯一出口"重新启用"回 IDLE

M3 §14.6 audit 化时，把 assert_transition_allowed 升级为同时写
StateTransitionRecord（不影响 ALLOWED_TRANSITIONS 形态）。
M3 §14.7 状态枚举完善（加 ARCHIVED）时，扩展 ALLOWED_TRANSITIONS dict。
"""
from asset_hub.errors import ValidationError
from asset_hub.models.asset import AssetStatus

ALLOWED_TRANSITIONS: dict[AssetStatus, set[AssetStatus]] = {
    AssetStatus.IDLE: {
        AssetStatus.IN_USE,        # 派发
        AssetStatus.MAINTENANCE,   # 送修
        AssetStatus.RETIRED,       # 退役
    },
    AssetStatus.IN_USE: {
        AssetStatus.IDLE,          # 归还
    },
    AssetStatus.MAINTENANCE: {
        AssetStatus.IDLE,          # 修好回库
        AssetStatus.RETIRED,       # 退役
    },
    AssetStatus.RETIRED: {
        AssetStatus.IDLE,          # 重新启用
    },
}


def is_transition_allowed(from_status: AssetStatus, to_status: AssetStatus) -> bool:
    return to_status in ALLOWED_TRANSITIONS[from_status]


def assert_transition_allowed(from_status: AssetStatus, to_status: AssetStatus) -> None:
    if to_status not in ALLOWED_TRANSITIONS[from_status]:
        raise ValidationError(
            f"不允许从 {from_status.value} 转到 {to_status.value}"
        )
