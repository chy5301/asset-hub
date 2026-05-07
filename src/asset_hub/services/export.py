"""
导出服务: CSV/XLSX 资产清单导出.

spec: docs/superpowers/specs/2026-05-07-m3c-export-design.md
"""

from __future__ import annotations

import csv
import io
import uuid

from sqlmodel import Session

from asset_hub.api.schemas.asset_type import CustomFieldDef
from asset_hub.models.asset import Asset, AssetStatus
from asset_hub.services.asset import AssetService
from asset_hub.services.asset_type import TypeService

# spec §B.4: 状态字段写人类标签 (与 frontend STATUS_META.label 同义)
# 后续 simplify 可消除 stats / asset CLI 字面量统一指向此 dict (不在 M3c 范围)
STATUS_LABELS: dict[AssetStatus, str] = {
    AssetStatus.IN_USE: "在用",
    AssetStatus.IDLE: "闲置",
    AssetStatus.MAINTENANCE: "维修中",
    AssetStatus.RETIRED: "已退役",
    AssetStatus.DISPOSED: "已处置",
}

# spec §B.7: 5 态 light 模式 OKLCH 转 sRGB ARGB hex.
# 输入 OKLCH 来自 frontend/src/styles/globals.css line 102-110 light 模式,
# 用 colour-science 实施期一次性算出 (脚本见 PR-1 plan Task 2).
# 与 frontend 视觉对齐, 但导出文件永远用 light hex (打印友好, 与浏览器
# dark/light 切换无关).
STATUS_HEX: dict[AssetStatus, str] = {
    AssetStatus.IN_USE: "FFBBF5CD",
    AssetStatus.IDLE: "FFE4ECF5",
    AssetStatus.MAINTENANCE: "FFFFDCA8",
    AssetStatus.RETIRED: "FFE5E8EB",
    AssetStatus.DISPOSED: "FFEEEEEE",
}


class ExportService:
    """资产清单 CSV/XLSX 导出. spec §B.2 / §2.2."""

    def __init__(
        self,
        session: Session,
        asset_service: AssetService,
        type_service: TypeService,
    ) -> None:
        self.session = session
        self.asset_service = asset_service
        self.type_service = type_service

    def _resolve_custom_fields(
        self, type_id: uuid.UUID | None
    ) -> list[CustomFieldDef]:
        """spec §B.2: type_id 显式锁定时返 type.custom_fields, 否则 []."""
        if type_id is None:
            return []
        return self.type_service.get_type(type_id).custom_fields

    def _build_rows(
        self,
        assets: list[Asset],
        custom_fields: list[CustomFieldDef],
    ) -> list[dict[str, str]]:
        """spec §B.3: 10 固定列 + custom_fields 平铺. 列序严格.

        idle_days 期望 caller 已调 AssetService.annotate_idle_days(assets);
        未 annotate 时 asset.idle_days 返 None → 兜底空字符串.
        """
        rows: list[dict[str, str]] = []
        for a in assets:
            row: dict[str, str] = {
                "资产编号": a.asset_code,
                "名称": a.name,
                "类型": a.type_name or "",
                "状态": STATUS_LABELS[a.status],
                "保管人": a.holder or "",
                "位置": a.location or "",
                "闲置天数": str(a.idle_days) if a.idle_days is not None else "",
                "入账日期": a.acquired_at.isoformat() if a.acquired_at else "",
                "铭牌编号": a.serial_number or "",
                "备注": a.notes or "",
            }
            for field in custom_fields:
                header = field.label or field.key
                row[header] = str((a.custom_data or {}).get(field.key, ""))
            rows.append(row)
        return rows

    def _render_csv(
        self,
        rows: list[dict[str, str]],
        column_names: list[str] | None = None,
    ) -> bytes:
        """spec §B.6: UTF-8 BOM + stdlib csv.writer.

        column_names 在 rows 非空时可省 (从 rows[0].keys() 推断);
        rows 空时必传 (0 结果仅 header 场景).
        """
        if column_names is None:
            if not rows:
                return b"\xef\xbb\xbf"
            column_names = list(rows[0].keys())

        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=column_names, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

        return b"\xef\xbb\xbf" + buf.getvalue().encode("utf-8")
