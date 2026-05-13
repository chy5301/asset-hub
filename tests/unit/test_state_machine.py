import pytest

from asset_hub.errors import IllegalTransitionError
from asset_hub.models.asset import AssetStatus
from asset_hub.models.state_transition import TransitionKind
from asset_hub.services.state_machine import TRANSITION_RULES, validate_transition


@pytest.mark.parametrize(
    "kind,from_status,expected_to",
    [
        (TransitionKind.CHECKOUT_INTERNAL, AssetStatus.IDLE, AssetStatus.IN_USE),
        (TransitionKind.CHECKOUT_EXTERNAL, AssetStatus.IDLE, AssetStatus.IN_USE),
        (TransitionKind.RETURN, AssetStatus.IN_USE, AssetStatus.IDLE),
        (TransitionKind.SEND_TO_MAINTENANCE, AssetStatus.IDLE, AssetStatus.MAINTENANCE),
        (
            TransitionKind.RECOVER_FROM_MAINTENANCE,
            AssetStatus.MAINTENANCE,
            AssetStatus.IDLE,
        ),
        (TransitionKind.RETIRE, AssetStatus.IDLE, AssetStatus.RETIRED),
        (TransitionKind.RETIRE, AssetStatus.MAINTENANCE, AssetStatus.RETIRED),
        (TransitionKind.REINSTATE, AssetStatus.RETIRED, AssetStatus.IDLE),
        (TransitionKind.DISPOSE, AssetStatus.RETIRED, AssetStatus.DISPOSED),
        (TransitionKind.DISPOSE, AssetStatus.MAINTENANCE, AssetStatus.DISPOSED),
    ],
)
def test_legal_transitions(kind, from_status, expected_to):
    to = validate_transition(from_status, kind, to_holder="X", to_location="Y")
    assert to == expected_to


@pytest.mark.parametrize(
    "kind,bad_from",
    [
        (k, s)
        for k, r in TRANSITION_RULES.items()
        for s in AssetStatus
        if s not in r.valid_from
    ],
)
def test_all_illegal_from_combinations_raise(kind, bad_from):
    with pytest.raises(IllegalTransitionError):
        validate_transition(bad_from, kind, to_holder="X", to_location="Y")


def test_required_holder_missing_raises():
    with pytest.raises(IllegalTransitionError, match="to_holder"):
        validate_transition(
            AssetStatus.IDLE, TransitionKind.CHECKOUT_INTERNAL, None, None
        )


def test_dispose_forced_null_rules():
    rule = TRANSITION_RULES[TransitionKind.DISPOSE]
    assert rule.holder_rule == "forced_null"
    assert rule.location_rule == "forced_null"


def test_disposed_is_terminal_for_every_kind():
    for kind, rule in TRANSITION_RULES.items():
        assert AssetStatus.DISPOSED not in rule.valid_from, (
            f"{kind} broke DISPOSED terminal invariant"
        )


# ---------------------------------------------------------------------------
# Phase 2.1 + 2.2 新测试（v2.0 spec §2.4）
# ---------------------------------------------------------------------------


def test_holder_rule_includes_keep():
    """HolderRule v2.0 加 'keep' 值。"""
    from typing import get_args

    from asset_hub.services.state_machine import HolderRule, LocationRule

    assert "keep" in get_args(HolderRule)
    assert "keep" in get_args(LocationRule)


# v2.0 完整 rule 表（参考 spec §2.4）
_EXPECTED_RULES = {
    TransitionKind.CHECKOUT_INTERNAL: (
        frozenset({AssetStatus.IDLE}),
        AssetStatus.IN_USE,
        "required",
        "keep",
    ),
    TransitionKind.CHECKOUT_EXTERNAL: (
        frozenset({AssetStatus.IDLE}),
        AssetStatus.IN_USE,
        "required",
        "keep",
    ),
    TransitionKind.RETURN: (
        frozenset({AssetStatus.IN_USE}),
        AssetStatus.IDLE,
        "optional",
        "keep",
    ),
    TransitionKind.SEND_TO_MAINTENANCE: (
        frozenset({AssetStatus.IDLE, AssetStatus.BROKEN}),
        AssetStatus.MAINTENANCE,
        "keep",
        "keep",
    ),
    TransitionKind.RECOVER_FROM_MAINTENANCE: (
        frozenset({AssetStatus.MAINTENANCE}),
        AssetStatus.IDLE,
        "keep",
        "keep",
    ),
    TransitionKind.RETIRE: (
        frozenset({AssetStatus.IDLE, AssetStatus.MAINTENANCE, AssetStatus.BROKEN}),
        AssetStatus.RETIRED,
        "keep",
        "keep",
    ),
    TransitionKind.REINSTATE: (
        frozenset({AssetStatus.RETIRED}),
        AssetStatus.IDLE,
        "keep",
        "keep",
    ),
    TransitionKind.DISPOSE: (
        frozenset({AssetStatus.RETIRED, AssetStatus.MAINTENANCE, AssetStatus.BROKEN}),
        AssetStatus.DISPOSED,
        "forced_null",
        "forced_null",
    ),
    TransitionKind.REASSIGN: (
        frozenset(
            {
                AssetStatus.IDLE,
                AssetStatus.IN_USE,
                AssetStatus.MAINTENANCE,
                AssetStatus.BROKEN,
                AssetStatus.RETIRED,
            }
        ),
        None,
        "keep",
        "keep",
    ),
    TransitionKind.REPORT_BROKEN: (
        frozenset({AssetStatus.IDLE, AssetStatus.IN_USE}),
        AssetStatus.BROKEN,
        "keep",
        "keep",
    ),
    TransitionKind.DECLARE_UNREPAIRABLE: (
        frozenset({AssetStatus.MAINTENANCE}),
        AssetStatus.BROKEN,
        "keep",
        "keep",
    ),
    TransitionKind.DISMISS: (
        frozenset({AssetStatus.BROKEN}),
        AssetStatus.IDLE,
        "keep",
        "keep",
    ),
}


@pytest.mark.parametrize("kind,expected", _EXPECTED_RULES.items())
def test_transition_rule_matches_v2_spec(kind, expected):
    from asset_hub.services.state_machine import TRANSITION_RULES as TR

    valid_from, to_status, holder_rule, location_rule = expected
    rule = TR[kind]
    assert rule.valid_from == valid_from
    assert rule.to_status == to_status
    assert rule.holder_rule == holder_rule
    assert rule.location_rule == location_rule


def test_transition_rules_only_12_kinds():
    from asset_hub.services.state_machine import TRANSITION_RULES as TR

    assert len(TR) == 12
    assert set(TR.keys()) == set(TransitionKind)


def test_persisted_checkout_states():
    """v2.0 派出延续集合 = {IN_USE, BROKEN}。"""
    from asset_hub.services.state_machine import PERSISTED_CHECKOUT_STATES

    assert PERSISTED_CHECKOUT_STATES == frozenset(
        {AssetStatus.IN_USE, AssetStatus.BROKEN}
    )
