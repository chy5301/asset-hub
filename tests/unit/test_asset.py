def test_asset_status_enum_includes_broken():
    """v2.0 AssetStatus 包含 BROKEN 故障态。"""
    from asset_hub.models.asset import AssetStatus

    assert AssetStatus.BROKEN == "BROKEN"
    assert AssetStatus.BROKEN.value == "BROKEN"
    expected = {"IDLE", "IN_USE", "MAINTENANCE", "BROKEN", "RETIRED", "DISPOSED"}
    assert {s.value for s in AssetStatus} == expected
