"""
导出服务: CSV/XLSX 资产清单导出.

spec: docs/superpowers/specs/2026-05-07-m3c-export-design.md
"""

from __future__ import annotations

from sqlmodel import Session

from asset_hub.models.asset import AssetStatus

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
    """导出服务. 详细方法签名 Task 3-7 落."""

    def __init__(self, session: Session) -> None:
        self.session = session
