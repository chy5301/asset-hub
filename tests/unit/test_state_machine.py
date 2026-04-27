"""state_machine 4 状态 × 转换合法性矩阵全测。"""

import pytest

from asset_hub.errors import ValidationError
from asset_hub.models.asset import AssetStatus
from asset_hub.services.state_machine import (
    ALLOWED_TRANSITIONS,
    assert_transition_allowed,
    is_transition_allowed,
)

# 7 条合法转换（spec D14）
LEGAL = [
    (AssetStatus.IDLE, AssetStatus.IN_USE),       # 派发
    (AssetStatus.IN_USE, AssetStatus.IDLE),       # 归还
    (AssetStatus.IDLE, AssetStatus.MAINTENANCE),  # 送修
    (AssetStatus.MAINTENANCE, AssetStatus.IDLE),  # 修好回库
    (AssetStatus.IDLE, AssetStatus.RETIRED),      # 退役
    (AssetStatus.MAINTENANCE, AssetStatus.RETIRED),  # 维修中退役
    (AssetStatus.RETIRED, AssetStatus.IDLE),      # 重新启用
]

# 9 条非法转换（spec D14 列举的不允许）
ILLEGAL = [
    (AssetStatus.IN_USE, AssetStatus.MAINTENANCE),  # 派发中送修
    (AssetStatus.IN_USE, AssetStatus.RETIRED),      # 派发中退役
    (AssetStatus.MAINTENANCE, AssetStatus.IN_USE),  # 维修中派发（不可）
    (AssetStatus.RETIRED, AssetStatus.IN_USE),      # 退役后派发
    (AssetStatus.RETIRED, AssetStatus.MAINTENANCE), # 退役后送修
    (AssetStatus.RETIRED, AssetStatus.RETIRED),     # 自循环
    (AssetStatus.IDLE, AssetStatus.IDLE),
    (AssetStatus.IN_USE, AssetStatus.IN_USE),
    (AssetStatus.MAINTENANCE, AssetStatus.MAINTENANCE),
]


@pytest.mark.parametrize("from_s, to_s", LEGAL)
def test_legal_transitions(from_s, to_s):
    assert is_transition_allowed(from_s, to_s) is True
    assert_transition_allowed(from_s, to_s)  # 不抛


@pytest.mark.parametrize("from_s, to_s", ILLEGAL)
def test_illegal_transitions_raise(from_s, to_s):
    assert is_transition_allowed(from_s, to_s) is False
    with pytest.raises(ValidationError, match=r"不允许从.*转到"):
        assert_transition_allowed(from_s, to_s)


def test_allowed_transitions_matrix_complete():
    """白盒检查：4 个状态都在矩阵中作为 key 存在。"""
    for status in AssetStatus:
        assert status in ALLOWED_TRANSITIONS
