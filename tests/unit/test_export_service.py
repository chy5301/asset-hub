"""ExportService 单元测试."""

from __future__ import annotations

import re

from asset_hub.models.asset import AssetStatus
from asset_hub.services.export import STATUS_HEX, STATUS_LABELS


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
