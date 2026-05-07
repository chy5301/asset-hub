"""ExportService 单元测试."""

from __future__ import annotations

import re
from datetime import date

from sqlmodel import Session

from asset_hub.models.asset import AssetStatus
from asset_hub.services.asset import AssetService
from asset_hub.services.asset_type import TypeService
from asset_hub.services.export import STATUS_HEX, STATUS_LABELS, ExportService


class TestStatusDicts:
    def test_status_labels_covers_5_enum_values(self):
        assert set(STATUS_LABELS.keys()) == set(AssetStatus)

    def test_status_labels_chinese(self):
        assert STATUS_LABELS[AssetStatus.IN_USE] == "在用"
        assert STATUS_LABELS[AssetStatus.IDLE] == "闲置"
        assert STATUS_LABELS[AssetStatus.MAINTENANCE] == "维修中"
        assert STATUS_LABELS[AssetStatus.RETIRED] == "已退役"
        assert STATUS_LABELS[AssetStatus.DISPOSED] == "已处置"

    def test_status_hex_covers_5_enum_values(self):
        assert set(STATUS_HEX.keys()) == set(AssetStatus)

    def test_status_hex_format(self):
        # ARGB hex: 8 大写 char, 前 2 char 是 FF (full alpha)
        for hex_val in STATUS_HEX.values():
            assert re.fullmatch(r"FF[0-9A-F]{6}", hex_val), (
                f"非法 ARGB hex: {hex_val!r}, 期望形如 'FFRRGGBB'"
            )


class TestResolveCustomFields:
    def test_returns_empty_when_type_id_none(self, session: Session):
        type_svc = TypeService(session)
        asset_svc = AssetService(session)
        svc = ExportService(session, asset_svc, type_svc)
        assert svc._resolve_custom_fields(None) == []

    def test_returns_type_custom_fields_when_locked(self, session: Session):
        type_svc = TypeService(session)
        asset_svc = AssetService(session)
        svc = ExportService(session, asset_svc, type_svc)

        t = type_svc.create_type(
            name="Laptop",
            code_prefix="NB",
            custom_fields=[
                {"key": "sn", "label": "铭牌编号", "type": "string", "required": False},
                {"key": "cpu", "label": "CPU", "type": "string", "required": False},
            ],
        )

        fields = svc._resolve_custom_fields(t.id)
        assert len(fields) == 2
        assert fields[0].key == "sn"
        assert fields[0].label == "铭牌编号"
        assert fields[1].key == "cpu"


class TestBuildRows:
    def test_column_order_no_custom_fields(self, session: Session):
        type_svc = TypeService(session)
        asset_svc = AssetService(session)
        svc = ExportService(session, asset_svc, type_svc)

        t = type_svc.create_type(name="Laptop", code_prefix="NB", custom_fields=[])
        a = asset_svc.register(name="A1", type_id=t.id, custom_data={})

        rows = svc._build_rows([a], custom_fields=[])
        assert len(rows) == 1
        keys = list(rows[0].keys())
        assert keys == [
            "资产编号",
            "名称",
            "类型",
            "状态",
            "保管人",
            "位置",
            "闲置天数",
            "入账日期",
            "铭牌编号",
            "备注",
        ]

    def test_status_chinese_label(self, session: Session):
        type_svc = TypeService(session)
        asset_svc = AssetService(session)
        svc = ExportService(session, asset_svc, type_svc)

        t = type_svc.create_type(name="L", code_prefix="LA", custom_fields=[])
        a = asset_svc.register(name="X", type_id=t.id, custom_data={})

        rows = svc._build_rows([a], custom_fields=[])
        assert rows[0]["状态"] == "闲置"  # register 默认 IDLE

    def test_acquired_at_iso_date(self, session: Session):
        type_svc = TypeService(session)
        asset_svc = AssetService(session)
        svc = ExportService(session, asset_svc, type_svc)

        t = type_svc.create_type(name="L", code_prefix="LB", custom_fields=[])
        a = asset_svc.register(
            name="X", type_id=t.id, custom_data={}, acquired_at=date(2026, 1, 15)
        )

        rows = svc._build_rows([a], custom_fields=[])
        assert rows[0]["入账日期"] == "2026-01-15"

    def test_acquired_at_none_empty_string(self, session: Session):
        type_svc = TypeService(session)
        asset_svc = AssetService(session)
        svc = ExportService(session, asset_svc, type_svc)

        t = type_svc.create_type(name="L", code_prefix="LC", custom_fields=[])
        a = asset_svc.register(name="X", type_id=t.id, custom_data={})

        rows = svc._build_rows([a], custom_fields=[])
        assert rows[0]["入账日期"] == ""

    def test_holder_location_sn_notes_none_empty_string(self, session: Session):
        type_svc = TypeService(session)
        asset_svc = AssetService(session)
        svc = ExportService(session, asset_svc, type_svc)

        t = type_svc.create_type(name="L", code_prefix="LD", custom_fields=[])
        a = asset_svc.register(name="X", type_id=t.id, custom_data={})

        rows = svc._build_rows([a], custom_fields=[])
        assert rows[0]["保管人"] == ""
        assert rows[0]["位置"] == ""
        assert rows[0]["铭牌编号"] == ""
        assert rows[0]["备注"] == ""

    def test_custom_fields_flattened_when_provided(self, session: Session):
        type_svc = TypeService(session)
        asset_svc = AssetService(session)
        svc = ExportService(session, asset_svc, type_svc)

        t = type_svc.create_type(
            name="Laptop", code_prefix="NBX",
            custom_fields=[
                {"key": "sn", "label": "铭牌编号 (custom)", "type": "string", "required": False},
                {"key": "cpu", "label": "CPU", "type": "string", "required": False},
            ],
        )
        a = asset_svc.register(
            name="X", type_id=t.id,
            custom_data={"sn": "SN-001", "cpu": "i9-12900K"},
        )

        custom_fields = svc._resolve_custom_fields(t.id)
        rows = svc._build_rows([a], custom_fields=custom_fields)

        keys = list(rows[0].keys())
        assert keys[-2:] == ["铭牌编号 (custom)", "CPU"]
        assert rows[0]["铭牌编号 (custom)"] == "SN-001"
        assert rows[0]["CPU"] == "i9-12900K"

    def test_custom_field_missing_value_empty_string(self, session: Session):
        type_svc = TypeService(session)
        asset_svc = AssetService(session)
        svc = ExportService(session, asset_svc, type_svc)

        t = type_svc.create_type(
            name="L", code_prefix="LE",
            custom_fields=[
                {"key": "sn", "label": "SN", "type": "string", "required": False},
            ],
        )
        a = asset_svc.register(name="X", type_id=t.id, custom_data={})

        rows = svc._build_rows([a], custom_fields=svc._resolve_custom_fields(t.id))
        assert rows[0]["SN"] == ""

    def test_idle_days_after_annotate(self, session: Session):
        """idle_days 由 annotate_idle_days 注入; _build_rows 期望 caller 已 annotate."""
        type_svc = TypeService(session)
        asset_svc = AssetService(session)
        svc = ExportService(session, asset_svc, type_svc)

        t = type_svc.create_type(name="L", code_prefix="LF", custom_fields=[])
        a = asset_svc.register(name="X", type_id=t.id, custom_data={})  # IDLE
        annotated = asset_svc.annotate_idle_days([a])  # 注入 _idle_days_value

        rows = svc._build_rows(annotated, custom_fields=[])
        assert rows[0]["闲置天数"] in {"0", "1"}  # 刚 register, 0 或 1 天

    def test_idle_days_none_without_annotate(self, session: Session):
        """未 annotate 的 asset, idle_days property 返 None → '' 兜底."""
        type_svc = TypeService(session)
        asset_svc = AssetService(session)
        svc = ExportService(session, asset_svc, type_svc)

        t = type_svc.create_type(name="L", code_prefix="LG", custom_fields=[])
        a = asset_svc.register(name="X", type_id=t.id, custom_data={})  # 不调 annotate

        rows = svc._build_rows([a], custom_fields=[])
        assert rows[0]["闲置天数"] == ""

    def test_empty_assets_returns_empty_list(self, session: Session):
        type_svc = TypeService(session)
        asset_svc = AssetService(session)
        svc = ExportService(session, asset_svc, type_svc)

        rows = svc._build_rows([], custom_fields=[])
        assert rows == []
