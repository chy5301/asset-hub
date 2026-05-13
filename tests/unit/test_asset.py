def test_asset_status_enum_includes_broken():
    """v2.0 AssetStatus 包含 BROKEN 故障态。"""
    from asset_hub.models.asset import AssetStatus

    assert AssetStatus.BROKEN == "BROKEN"
    assert AssetStatus.BROKEN.value == "BROKEN"
    expected = {"IDLE", "IN_USE", "MAINTENANCE", "BROKEN", "RETIRED", "DISPOSED"}
    assert {s.value for s in AssetStatus} == expected


def test_asset_has_model_field(session):
    """Asset 模型应有 nullable model 字段，位置在 name 与 type_id 之间。"""
    from asset_hub.models.asset import Asset

    # 字段存在性
    assert "model" in Asset.model_fields
    # nullable
    field = Asset.model_fields["model"]
    assert field.annotation == (str | None)
    assert field.default is None
