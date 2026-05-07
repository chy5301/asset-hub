"""
导出服务: CSV/XLSX 资产清单导出.

spec: docs/superpowers/specs/2026-05-07-m3c-export-design.md
"""

from __future__ import annotations

import csv
import io
import uuid

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
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

    _SHEET_NAME = "资产清单"
    _STATUS_COLUMN_HEADER = "状态"
    _NOTES_COLUMN_HEADER = "备注"
    _COL_WIDTH_DEFAULT_CAP = 50
    _COL_WIDTH_NOTES_CAP = 60

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

    def _render_xlsx(
        self,
        rows: list[dict[str, str]],
        column_names: list[str],
    ) -> bytes:
        """spec §B.7 / §B.7.1: openpyxl + 5 态 PatternFill + freeze A2 + autofilter."""
        wb = Workbook()
        ws = wb.active
        ws.title = self._SHEET_NAME

        # Header row 1, bold
        bold_font = Font(bold=True)
        for col_idx, name in enumerate(column_names, start=1):
            cell = ws.cell(row=1, column=col_idx, value=name)
            cell.font = bold_font

        # Data rows
        wrap_align = Alignment(wrap_text=True, vertical="top")
        status_col_idx = (
            column_names.index(self._STATUS_COLUMN_HEADER) + 1
            if self._STATUS_COLUMN_HEADER in column_names
            else None
        )
        for row_idx, row in enumerate(rows, start=2):
            for col_idx, name in enumerate(column_names, start=1):
                cell = ws.cell(row=row_idx, column=col_idx, value=row.get(name, ""))
                cell.alignment = wrap_align
                if col_idx == status_col_idx:
                    status_value = row.get(name, "")
                    status_enum = self._label_to_enum(status_value)
                    if status_enum is not None:
                        hex_argb = STATUS_HEX[status_enum]
                        cell.fill = PatternFill(
                            start_color=hex_argb,
                            end_color=hex_argb,
                            fill_type="solid",
                        )

        # Freeze + autofilter
        ws.freeze_panes = "A2"
        max_row = len(rows) + 1
        max_col_letter = get_column_letter(len(column_names))
        ws.auto_filter.ref = f"A1:{max_col_letter}{max_row}"

        # Column width auto-fit cap
        for col_idx, name in enumerate(column_names, start=1):
            letter = get_column_letter(col_idx)
            cap = (
                self._COL_WIDTH_NOTES_CAP
                if name == self._NOTES_COLUMN_HEADER
                else self._COL_WIDTH_DEFAULT_CAP
            )
            max_chars = len(name)
            for row in rows:
                value = row.get(name, "")
                # 中文字符按 ~2x 算 (XLSX 列宽单位约等于英文字符)
                width = sum(2 if ord(c) > 127 else 1 for c in value)
                if width > max_chars:
                    max_chars = width
            ws.column_dimensions[letter].width = min(max_chars + 2, cap)

        # 序列化 bytes
        buf = io.BytesIO()
        wb.save(buf)
        return buf.getvalue()

    @staticmethod
    def _label_to_enum(label: str) -> AssetStatus | None:
        """状态中文标签反查 enum (仅用于 XLSX 染色; 找不到返 None 不染色)."""
        for enum_val, lbl in STATUS_LABELS.items():
            if lbl == label:
                return enum_val
        return None
