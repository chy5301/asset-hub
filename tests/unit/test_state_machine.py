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
        (TransitionKind.RECOVER_FROM_MAINTENANCE, AssetStatus.MAINTENANCE, AssetStatus.IDLE),
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


@pytest.mark.parametrize("from_status", list(AssetStatus))
def test_relocate_returns_same_status_except_disposed(from_status):
    if from_status == AssetStatus.DISPOSED:
        with pytest.raises(IllegalTransitionError):
            validate_transition(from_status, TransitionKind.RELOCATE, None, "loc")
    else:
        to = validate_transition(from_status, TransitionKind.RELOCATE, None, "loc")
        assert to == from_status


@pytest.mark.parametrize("from_status", list(AssetStatus))
def test_transfer_holder_returns_same_status_except_disposed(from_status):
    if from_status == AssetStatus.DISPOSED:
        with pytest.raises(IllegalTransitionError):
            validate_transition(from_status, TransitionKind.TRANSFER_HOLDER, "h", None)
    else:
        to = validate_transition(from_status, TransitionKind.TRANSFER_HOLDER, "h", None)
        assert to == from_status


@pytest.mark.parametrize(
    "kind,bad_from",
    [(k, s) for k, r in TRANSITION_RULES.items() for s in AssetStatus if s not in r.valid_from],
)
def test_all_illegal_from_combinations_raise(kind, bad_from):
    with pytest.raises(IllegalTransitionError):
        validate_transition(bad_from, kind, to_holder="X", to_location="Y")


def test_required_holder_missing_raises():
    with pytest.raises(IllegalTransitionError, match="to_holder"):
        validate_transition(AssetStatus.IDLE, TransitionKind.CHECKOUT_INTERNAL, None, None)


def test_required_location_missing_raises():
    with pytest.raises(IllegalTransitionError, match="to_location"):
        validate_transition(AssetStatus.IDLE, TransitionKind.RELOCATE, None, None)


def test_dispose_forced_null_rules():
    rule = TRANSITION_RULES[TransitionKind.DISPOSE]
    assert rule.holder_rule == "forced_null"
    assert rule.location_rule == "forced_null"


def test_relocate_holder_ignored_rule():
    rule = TRANSITION_RULES[TransitionKind.RELOCATE]
    assert rule.holder_rule == "ignored"


def test_disposed_is_terminal_for_every_kind():
    for kind, rule in TRANSITION_RULES.items():
        assert AssetStatus.DISPOSED not in rule.valid_from, (
            f"{kind} broke DISPOSED terminal invariant"
        )
