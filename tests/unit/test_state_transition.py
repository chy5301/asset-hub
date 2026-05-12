def test_transition_kind_v2_set():
    """v2.0 TransitionKind 12 个 = v1.0 10 - {RELOCATE, TRANSFER_HOLDER} + {REASSIGN, REPORT_BROKEN, DECLARE_UNREPAIRABLE, DISMISS}。"""
    from asset_hub.models.state_transition import TransitionKind

    expected = {
        "CHECKOUT_INTERNAL", "CHECKOUT_EXTERNAL", "RETURN",
        "SEND_TO_MAINTENANCE", "RECOVER_FROM_MAINTENANCE",
        "RETIRE", "REINSTATE", "DISPOSE",
        "REASSIGN",
        "REPORT_BROKEN", "DECLARE_UNREPAIRABLE", "DISMISS",
    }
    assert {k.value for k in TransitionKind} == expected
    assert not hasattr(TransitionKind, "RELOCATE")
    assert not hasattr(TransitionKind, "TRANSFER_HOLDER")
