# M3c PR-1 实施计划: CSV/XLSX 导出后端

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 后端 `GET /api/export` 单端点 + `ExportService` + openpyxl 集成,服务 PR-2 前端导出按钮.

**Architecture:** `ExportService` 复用 `AssetService.list_assets` 拉数据,按 spec §B.2 决定 custom_fields 平铺策略,产出 `(bytes, filename)`. CSV 走 stdlib `csv.writer` + UTF-8 BOM; XLSX 走 openpyxl + 5 态 `PatternFill` cell 染色 + freeze `A2` + autofilter + 列宽 cap. Router `GET /api/export` 单端点, `format=csv|xlsx` 必填.

**Tech Stack:** FastAPI / SQLModel / openpyxl 3.1+ / Python stdlib csv / pytest.

**Spec:** [`docs/superpowers/specs/2026-05-07-m3c-export-design.md`](../specs/2026-05-07-m3c-export-design.md)

**前置约束:**
- M3a (状态机基建) ✅ + M3b (看板) ✅ 都已 merged 到 main
- `AssetService.list_assets` 完整 filter 签名已落地(M3b PR-1: type_id/status/holder/q/include_retired/include_disposed/sort_by/sort_order/limit/offset)
- `Asset.idle_days` @property 已落地(M3b PR-1)
- 5 态 OKLCH token 已在 `frontend/src/styles/globals.css` line 102-111(`--status-in-use/-idle/-maintenance/-retired/-disposed`)
- 后端无集中 `STATUS_LABELS` dict,M3c 在 `services/export.py` 内落一份,后续 simplify pass 可消除 stats CLI / asset CLI 字面量(**不在本 PR 范围**)

**任务总览**(10 任务):

1. 起分支 + 加 openpyxl 依赖
2. `STATUS_LABELS` + `STATUS_HEX` dict(含 OKLCH→ARGB hex 转算)
3. `ExportService.__init__` + `_resolve_custom_fields`(TDD)
4. `ExportService._build_rows`(TDD)
5. `ExportService._render_csv`(TDD)
6. `ExportService._render_xlsx`(TDD)
7. `ExportService.export` 整合 + filename(TDD)
8. `GET /api/export` router + register(TDD with `TestClient`)
9. 后端最终验证 + simplify pass
10. PR-1 合并

---

## Task 1: 起分支 + 加 openpyxl 依赖

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1.1: 起分支**

```bash
git checkout main
git pull --ff-only origin main 2>&1 || true   # 单人项目 origin 通常已最新
git checkout -b feat/m3c-pr1-backend
```

- [ ] **Step 1.2: 加 openpyxl 到 pyproject.toml**

打开 `pyproject.toml`,在 `[project]` 段的 `dependencies` 列表中,按字母序追加 `"openpyxl>=3.1"`. 例如(原文 dependencies 视项目而定,新增行示意):

```toml
dependencies = [
    "alembic>=1.13",
    "fastapi>=0.115",
    # ... 其他已有 deps ...
    "openpyxl>=3.1",
    # ... 其他已有 deps ...
]
```

具体插入位置看现有 dependencies 列表的字母序;如已无序,在末尾追加即可.

- [ ] **Step 1.3: `uv sync` 安装**

```bash
uv sync
```

预期: 输出 `Resolved N packages` + `Prepared M packages` + `openpyxl==X.Y.Z`(版本至少 3.1).

- [ ] **Step 1.4: 验证 import**

```bash
uv run python -c "import openpyxl; print(openpyxl.__version__)"
```

预期: 打印版本号(>=3.1.x).

- [ ] **Step 1.5: 提交**

```bash
git add pyproject.toml uv.lock
git commit -m "$(cat <<'EOF'
chore(deps): 加 openpyxl 3.1+ 依赖 (M3c XLSX 导出)
EOF
)"
```

---

## Task 2: `STATUS_LABELS` + `STATUS_HEX` dict

**Files:**
- Create: `src/asset_hub/services/export.py`(初始骨架)
- Test: `tests/unit/test_export_service.py`(初始 + Task 2 case)

`STATUS_LABELS` 是 `AssetStatus` enum → 中文 label 映射(spec §B.4); `STATUS_HEX` 是 `AssetStatus` → ARGB hex 字符串(spec §B.7),实际 hex 实施期用 OKLCH 转算工具(下方 Step 2.1)算出.

- [ ] **Step 2.1: 算 5 态 ARGB hex**

`frontend/src/styles/globals.css` line 102-111 light 模式 5 态 OKLCH 值如下,用 [https://oklch.com/](https://oklch.com/) 工具或 Python lib `colour-science` 转 sRGB hex:

| AssetStatus | OKLCH (light) | 期望转算后 sRGB hex |
|---|---|---|
| `IN_USE` | `oklch(0.92 0.08 155)` | (浅绿,~ `D8F0DC`) |
| `IDLE` | `oklch(0.94 0.015 247)` | (浅蓝灰,~ `EDF0F4`) |
| `MAINTENANCE` | `oklch(0.93 0.09 65)` | (浅橙黄,~ `F5DCB8`) |
| `RETIRED` | `oklch(0.93 0.005 247)` | (浅灰,~ `EBECEE`) |
| `DISPOSED` | `oklch(0.95 0.000 0)` | (近白,~ `F0F0F0`) |

> 上面表格的 sRGB hex 是估算参考,**不要直接用**——开 [https://oklch.com/](https://oklch.com/),把 5 个 OKLCH 值粘进去,复制工具显示的真实 sRGB hex(6 char),前缀 `FF`(alpha) 拼成 8 char ARGB.例如 `FFD8F0DC`.

记录最终 5 个 ARGB hex 值,写入下面 Step 2.2 的 `STATUS_HEX` dict.

- [ ] **Step 2.2: 创建 `src/asset_hub/services/export.py` 骨架**

```python
"""
导出服务: CSV/XLSX 资产清单导出.

spec: docs/superpowers/specs/2026-05-07-m3c-export-design.md
"""
from __future__ import annotations

import uuid
from typing import Literal

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

# spec §B.7: 5 态 light 模式 OKLCH 转 sRGB ARGB hex (实施期 oklch.com 算)
# 与 frontend globals.css `--status-*` light 模式视觉对齐, 但永远用 light hex
# (导出文件需打印友好, 与浏览器 dark/light 切换无关)
STATUS_HEX: dict[AssetStatus, str] = {
    AssetStatus.IN_USE: "FF<6char>",       # TODO Step 2.1 算的 hex
    AssetStatus.IDLE: "FF<6char>",
    AssetStatus.MAINTENANCE: "FF<6char>",
    AssetStatus.RETIRED: "FF<6char>",
    AssetStatus.DISPOSED: "FF<6char>",
}


class ExportService:
    """导出服务. 详细方法签名 Task 3-7 落."""

    def __init__(self, session: Session) -> None:
        self.session = session
```

填充 `STATUS_HEX` dict 的实际 8-char ARGB 值(替换 5 处 `FF<6char>` 占位).例如:

```python
STATUS_HEX: dict[AssetStatus, str] = {
    AssetStatus.IN_USE: "FFD8F0DC",       # 实际值以 Step 2.1 工具输出为准
    AssetStatus.IDLE: "FFEDF0F4",
    AssetStatus.MAINTENANCE: "FFF5DCB8",
    AssetStatus.RETIRED: "FFEBECEE",
    AssetStatus.DISPOSED: "FFF0F0F0",
}
```

- [ ] **Step 2.3: 写 dict 健全性测试**

`tests/unit/test_export_service.py`(新文件):

```python
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
```

- [ ] **Step 2.4: 跑测试**

```bash
uv run pytest tests/unit/test_export_service.py::TestStatusDicts -v
```

预期: 4 PASS.若 `STATUS_HEX` 任何 hex 不符合 `FF[0-9A-F]{6}` 格式(如带小写、长度错、含 `<6char>` 占位),会失败 → 修 dict 后重跑.

- [ ] **Step 2.5: 提交**

```bash
git add src/asset_hub/services/export.py tests/unit/test_export_service.py
git commit -m "$(cat <<'EOF'
feat(export): STATUS_LABELS + STATUS_HEX dict (M3c PR-1 第 1 步)

5 态人类标签 + light 模式 OKLCH 转 sRGB ARGB hex (用 oklch.com 算).
service 骨架先 stub, Task 3-7 填充方法.
EOF
)"
```

---

## Task 3: `_resolve_custom_fields`(TDD)

**Files:**
- Modify: `src/asset_hub/services/export.py`
- Test: `tests/unit/test_export_service.py`

`_resolve_custom_fields(type_id)` 实现 spec §B.2 策略: type_id 显式锁定单一 type → 返该 type 的 `custom_fields` 列表; type_id None → 返 `[]`.

- [ ] **Step 3.1: 看 `TypeService` 与 `CustomFieldDef` 现状**

```bash
grep -n "class TypeService\|def get_type\|class CustomFieldDef" src/asset_hub/services/type.py src/asset_hub/models/type.py 2>&1 | head -10
```

记录 `TypeService.get_type` 签名 + `CustomFieldDef` 字段(应至少含 `key: str` + `label: str | None`).Task 4 用 `field.key` 拉 `custom_data` value, `field.label or field.key` 作 XLSX/CSV header.

- [ ] **Step 3.2: 写测试**

在 `tests/unit/test_export_service.py` 追加:

```python
import pytest
from sqlmodel import Session

from asset_hub.services.asset import AssetService
from asset_hub.services.export import ExportService
from asset_hub.services.type import TypeService


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
```

注: `session` fixture 已在 `tests/conftest.py`(M3a 落).如未注入, 看 `tests/unit/test_type_service.py` 现有 fixture import 写法对齐.

- [ ] **Step 3.3: 跑测试(应失败)**

```bash
uv run pytest tests/unit/test_export_service.py::TestResolveCustomFields -v
```

预期: FAIL — `ExportService.__init__` 当前只接 `session` 一个参数; `_resolve_custom_fields` 还没实现.

- [ ] **Step 3.4: 改 `ExportService.__init__` + 实现 `_resolve_custom_fields`**

`src/asset_hub/services/export.py` 内,把 `ExportService` 类替换为:

```python
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
```

文件顶部 import 段加(按字母序):

```python
from asset_hub.models.type import CustomFieldDef
from asset_hub.services.asset import AssetService
from asset_hub.services.type import TypeService
```

- [ ] **Step 3.5: 跑测试(应通过)**

```bash
uv run pytest tests/unit/test_export_service.py -v
```

预期: 6 PASS(Task 2 的 4 + Task 3 的 2).

- [ ] **Step 3.6: 提交**

```bash
git add src/asset_hub/services/export.py tests/unit/test_export_service.py
git commit -m "$(cat <<'EOF'
feat(export): ExportService.__init__ + _resolve_custom_fields

spec §B.2: type_id 显式锁定时返 type.custom_fields 用于 XLSX/CSV 列平铺,
否则返 [] 跳过平铺.
EOF
)"
```

---

## Task 4: `_build_rows`(TDD)

**Files:**
- Modify: `src/asset_hub/services/export.py`
- Test: `tests/unit/test_export_service.py`

`_build_rows(assets, custom_fields)` 把 ORM `Asset` 列表 + 平铺字段定义,转成 `list[dict[str, str]]`,key 是中文 header,value 是已格式化字符串.spec §2.2 + §B.3 + §B.4 决议.

列序(必须严格):

```
资产编号 / 名称 / 类型 / 状态 / 保管人 / 位置 / 闲置天数 / 入账日期 / 铭牌编号 / 备注
+ [field.label or field.key for field in custom_fields]
```

格式化规则:

| 字段 | None / null 时 | 非 null 时 |
|---|---|---|
| `asset_code` / `name` | 不会 None(NOT NULL) | 原样 |
| `type_name` | "" | 原样 |
| `status` | 不会 None | `STATUS_LABELS[asset.status]` |
| `holder` / `location` / `serial_number` / `notes` | "" | 原样 |
| `idle_days` | "0"(idle_days 是 @property, 一定有值;若 IN_USE 等非 IDLE 状态,@property 返 None,转 "") | `str(int)` |
| `acquired_at` | "" | `acquired_at.isoformat()`(`date` → `YYYY-MM-DD`) |
| custom field | "" | `str(asset.custom_data.get(field.key, ""))`(v1 简化, type-aware formatter 留 v2) |

- [ ] **Step 4.1: 看 `Asset` model 字段 + `idle_days` @property**

```bash
grep -n "class Asset\|idle_days\|acquired_at\|custom_data" src/asset_hub/models/asset.py 2>&1 | head -20
```

确认 `acquired_at` 类型(`date | None`?), `idle_days` 是 `int | None` @property, `custom_data: dict | None`.

- [ ] **Step 4.2: 写测试**

`tests/unit/test_export_service.py` 追加:

```python
from datetime import date

from asset_hub.models.asset import Asset, AssetStatus


class TestBuildRows:
    def test_column_order_no_custom_fields(self, session: Session):
        type_svc = TypeService(session)
        asset_svc = AssetService(session)
        svc = ExportService(session, asset_svc, type_svc)

        t = type_svc.create_type(name="Laptop", code_prefix="NB", custom_fields=[])
        a = asset_svc.register(name="A1", type_id=t.id, custom_data={})

        rows = svc._build_rows([a], custom_fields=[])
        assert len(rows) == 1
        # spec §B.3 列序
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

        t = type_svc.create_type(name="L", code_prefix="L", custom_fields=[])
        a = asset_svc.register(name="X", type_id=t.id, custom_data={})

        rows = svc._build_rows([a], custom_fields=[])
        # 新 register 的资产默认 IDLE
        assert rows[0]["状态"] == "闲置"

    def test_acquired_at_iso_date(self, session: Session):
        type_svc = TypeService(session)
        asset_svc = AssetService(session)
        svc = ExportService(session, asset_svc, type_svc)

        t = type_svc.create_type(name="L", code_prefix="L", custom_fields=[])
        a = asset_svc.register(
            name="X", type_id=t.id, custom_data={}, acquired_at=date(2026, 1, 15)
        )

        rows = svc._build_rows([a], custom_fields=[])
        assert rows[0]["入账日期"] == "2026-01-15"

    def test_acquired_at_none_empty_string(self, session: Session):
        type_svc = TypeService(session)
        asset_svc = AssetService(session)
        svc = ExportService(session, asset_svc, type_svc)

        t = type_svc.create_type(name="L", code_prefix="L", custom_fields=[])
        a = asset_svc.register(name="X", type_id=t.id, custom_data={})  # 无 acquired_at

        rows = svc._build_rows([a], custom_fields=[])
        assert rows[0]["入账日期"] == ""

    def test_holder_location_sn_notes_none_empty_string(self, session: Session):
        type_svc = TypeService(session)
        asset_svc = AssetService(session)
        svc = ExportService(session, asset_svc, type_svc)

        t = type_svc.create_type(name="L", code_prefix="L", custom_fields=[])
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
            name="Laptop",
            code_prefix="NB",
            custom_fields=[
                {"key": "sn", "label": "铭牌编号 (custom)", "type": "string", "required": False},
                {"key": "cpu", "label": "CPU", "type": "string", "required": False},
            ],
        )
        a = asset_svc.register(
            name="X",
            type_id=t.id,
            custom_data={"sn": "SN-001", "cpu": "i9-12900K"},
        )

        custom_fields = svc._resolve_custom_fields(t.id)
        rows = svc._build_rows([a], custom_fields=custom_fields)

        # custom 列追加在固定列之后, 列名用 field.label
        keys = list(rows[0].keys())
        assert keys[-2:] == ["铭牌编号 (custom)", "CPU"]
        assert rows[0]["铭牌编号 (custom)"] == "SN-001"
        assert rows[0]["CPU"] == "i9-12900K"

    def test_custom_field_missing_value_empty_string(self, session: Session):
        type_svc = TypeService(session)
        asset_svc = AssetService(session)
        svc = ExportService(session, asset_svc, type_svc)

        t = type_svc.create_type(
            name="L",
            code_prefix="L",
            custom_fields=[
                {"key": "sn", "label": "SN", "type": "string", "required": False},
            ],
        )
        a = asset_svc.register(name="X", type_id=t.id, custom_data={})  # custom_data 不含 sn

        rows = svc._build_rows([a], custom_fields=svc._resolve_custom_fields(t.id))
        assert rows[0]["SN"] == ""

    def test_idle_days_for_idle_asset_int_str(self, session: Session):
        type_svc = TypeService(session)
        asset_svc = AssetService(session)
        svc = ExportService(session, asset_svc, type_svc)

        t = type_svc.create_type(name="L", code_prefix="L", custom_fields=[])
        a = asset_svc.register(name="X", type_id=t.id, custom_data={})  # IDLE since now

        rows = svc._build_rows([a], custom_fields=[])
        # 刚 register, idle_days 应为 0 或 1
        assert rows[0]["闲置天数"] in {"0", "1"}

    def test_empty_assets_returns_empty_list(self, session: Session):
        type_svc = TypeService(session)
        asset_svc = AssetService(session)
        svc = ExportService(session, asset_svc, type_svc)

        rows = svc._build_rows([], custom_fields=[])
        assert rows == []
```

- [ ] **Step 4.3: 跑测试(应失败)**

```bash
uv run pytest tests/unit/test_export_service.py::TestBuildRows -v
```

预期: 全部 FAIL — `_build_rows` 还没实现.

- [ ] **Step 4.4: 实现 `_build_rows`**

在 `src/asset_hub/services/export.py` `ExportService` 内追加方法:

```python
    def _build_rows(
        self,
        assets: list[Asset],
        custom_fields: list[CustomFieldDef],
    ) -> list[dict[str, str]]:
        """spec §B.3: 10 固定列 + custom_fields 平铺. 列序严格."""
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
```

文件顶部 import 段加:

```python
from asset_hub.models.asset import Asset
```

(`AssetStatus` 已 import.)

- [ ] **Step 4.5: 跑测试(应通过)**

```bash
uv run pytest tests/unit/test_export_service.py -v
```

预期: 16 PASS(Task 2 的 4 + Task 3 的 2 + Task 4 的 9 + 1 个 empty list).

> **重要**: `Asset.type_name` 是 M3a 落的 @property; 若 grep 发现实际名是别的属性(如 `type_name_cached`), 改 `_build_rows` 内对应取值.同样 `idle_days` 是 @property, 验 `Asset.idle_days` 实际可用.

- [ ] **Step 4.6: 提交**

```bash
git add src/asset_hub/services/export.py tests/unit/test_export_service.py
git commit -m "$(cat <<'EOF'
feat(export): ExportService._build_rows (10 固定列 + custom_fields 平铺)

spec §B.3 列序; spec §B.4 status 写人类标签; acquired_at YYYY-MM-DD;
None 字段统一空字符串; custom_field 用 field.label as header,
custom_data.get 用 field.key 取值, str() 兜底 (v1 简化).
EOF
)"
```

---

## Task 5: `_render_csv`(TDD)

**Files:**
- Modify: `src/asset_hub/services/export.py`
- Test: `tests/unit/test_export_service.py`

`_render_csv(rows)` 把 `list[dict[str, str]]` 渲染为 UTF-8 BOM 前缀的 CSV bytes.spec §B.6.

- [ ] **Step 5.1: 写测试**

`tests/unit/test_export_service.py` 追加:

```python
class TestRenderCsv:
    def test_starts_with_utf8_bom(self, session: Session):
        type_svc = TypeService(session)
        asset_svc = AssetService(session)
        svc = ExportService(session, asset_svc, type_svc)

        t = type_svc.create_type(name="L", code_prefix="L", custom_fields=[])
        a = asset_svc.register(name="X", type_id=t.id, custom_data={})
        rows = svc._build_rows([a], custom_fields=[])

        data = svc._render_csv(rows)
        # UTF-8 BOM = \xef\xbb\xbf
        assert data.startswith(b"\xef\xbb\xbf"), f"missing BOM, got {data[:10]!r}"

    def test_header_row_chinese(self, session: Session):
        type_svc = TypeService(session)
        asset_svc = AssetService(session)
        svc = ExportService(session, asset_svc, type_svc)

        t = type_svc.create_type(name="L", code_prefix="L", custom_fields=[])
        a = asset_svc.register(name="X", type_id=t.id, custom_data={})
        rows = svc._build_rows([a], custom_fields=[])

        data = svc._render_csv(rows)
        text = data.decode("utf-8-sig")  # decode 自动跳 BOM
        first_line = text.splitlines()[0]
        assert first_line.startswith("资产编号,名称,类型,状态,")

    def test_empty_rows_writes_header_only(self, session: Session):
        type_svc = TypeService(session)
        asset_svc = AssetService(session)
        svc = ExportService(session, asset_svc, type_svc)

        # rows 空 → 渲染需要 header, 但 dict 没有 keys 来源
        # 决策: empty rows + 必须传 column_names 给渲染层
        # 或: _render_csv 接受 empty rows 直接返 BOM + 空 (无 header)
        # spec §3 "0 结果: 仅 header"; 所以这里需要明确 column_names 参数
        # 改签名: _render_csv(rows, column_names) 必填
        column_names = [
            "资产编号", "名称", "类型", "状态", "保管人", "位置",
            "闲置天数", "入账日期", "铭牌编号", "备注",
        ]
        data = svc._render_csv([], column_names=column_names)
        text = data.decode("utf-8-sig")
        lines = text.strip().splitlines()
        assert len(lines) == 1
        assert lines[0] == ",".join(column_names)

    def test_csv_escape_comma_quote_newline(self, session: Session):
        type_svc = TypeService(session)
        asset_svc = AssetService(session)
        svc = ExportService(session, asset_svc, type_svc)

        t = type_svc.create_type(name="L", code_prefix="L", custom_fields=[])
        a = asset_svc.register(
            name='含,逗号"引号\n换行',
            type_id=t.id,
            custom_data={},
        )
        rows = svc._build_rows([a], custom_fields=[])

        data = svc._render_csv(rows, column_names=list(rows[0].keys()))
        text = data.decode("utf-8-sig")
        # 含逗号 / 引号 / 换行的字段必须包在双引号内, 内部双引号 escape 为 ""
        assert '"含,逗号""引号' in text
```

- [ ] **Step 5.2: 跑测试(应失败)**

```bash
uv run pytest tests/unit/test_export_service.py::TestRenderCsv -v
```

预期: FAIL — `_render_csv` 没实现.

- [ ] **Step 5.3: 实现 `_render_csv`**

`src/asset_hub/services/export.py` `ExportService` 内追加:

```python
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
                # 0 行且无 column_names 兜底返空 BOM, 调用方应总是传 column_names
                return b"\xef\xbb\xbf"
            column_names = list(rows[0].keys())

        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=column_names, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

        return b"\xef\xbb\xbf" + buf.getvalue().encode("utf-8")
```

文件顶部 import 段加:

```python
import csv
import io
```

- [ ] **Step 5.4: 跑测试(应通过)**

```bash
uv run pytest tests/unit/test_export_service.py -v
```

预期: 20 PASS(Task 4 的 16 + 4 个 csv).

- [ ] **Step 5.5: 提交**

```bash
git add src/asset_hub/services/export.py tests/unit/test_export_service.py
git commit -m "$(cat <<'EOF'
feat(export): _render_csv (UTF-8 BOM + stdlib csv.writer)

spec §B.6: BOM 前缀让 Excel 正确识别 UTF-8 中文; csv.DictWriter 自动
escape 逗号/引号/换行; 0 行场景由 column_names 参数显式传入 header.
EOF
)"
```

---

## Task 6: `_render_xlsx`(TDD)

**Files:**
- Modify: `src/asset_hub/services/export.py`
- Test: `tests/unit/test_export_service.py`

`_render_xlsx(rows, column_names)` openpyxl 渲染.spec §B.7 + §B.7.1:
- sheet name "资产清单"
- header row 1, bold
- `freeze_panes = "A2"`
- `auto_filter.ref` = 全数据范围
- 状态列 cell.fill `PatternFill(start_color=hex, end_color=hex, fill_type="solid")` 按 STATUS_HEX
- 列宽 cap 50(notes 列 cap 60) + `wrap_text=True`

- [ ] **Step 6.1: 写测试**

`tests/unit/test_export_service.py` 追加:

```python
import io as _io

import openpyxl


class TestRenderXlsx:
    @staticmethod
    def _load(data: bytes):
        return openpyxl.load_workbook(_io.BytesIO(data))

    def test_sheet_name_assets_list(self, session: Session):
        type_svc = TypeService(session)
        asset_svc = AssetService(session)
        svc = ExportService(session, asset_svc, type_svc)

        t = type_svc.create_type(name="L", code_prefix="L", custom_fields=[])
        a = asset_svc.register(name="X", type_id=t.id, custom_data={})
        rows = svc._build_rows([a], custom_fields=[])

        data = svc._render_xlsx(rows, column_names=list(rows[0].keys()))
        wb = self._load(data)
        assert "资产清单" in wb.sheetnames

    def test_header_row_bold(self, session: Session):
        type_svc = TypeService(session)
        asset_svc = AssetService(session)
        svc = ExportService(session, asset_svc, type_svc)

        t = type_svc.create_type(name="L", code_prefix="L", custom_fields=[])
        a = asset_svc.register(name="X", type_id=t.id, custom_data={})
        rows = svc._build_rows([a], custom_fields=[])

        data = svc._render_xlsx(rows, column_names=list(rows[0].keys()))
        ws = self._load(data)["资产清单"]
        # row 1 col 1 = "资产编号"
        assert ws.cell(row=1, column=1).value == "资产编号"
        assert ws.cell(row=1, column=1).font.bold is True

    def test_freeze_panes_a2(self, session: Session):
        type_svc = TypeService(session)
        asset_svc = AssetService(session)
        svc = ExportService(session, asset_svc, type_svc)

        t = type_svc.create_type(name="L", code_prefix="L", custom_fields=[])
        a = asset_svc.register(name="X", type_id=t.id, custom_data={})
        rows = svc._build_rows([a], custom_fields=[])

        data = svc._render_xlsx(rows, column_names=list(rows[0].keys()))
        ws = self._load(data)["资产清单"]
        assert ws.freeze_panes == "A2"

    def test_autofilter_full_range(self, session: Session):
        type_svc = TypeService(session)
        asset_svc = AssetService(session)
        svc = ExportService(session, asset_svc, type_svc)

        t = type_svc.create_type(name="L", code_prefix="L", custom_fields=[])
        a = asset_svc.register(name="X", type_id=t.id, custom_data={})
        rows = svc._build_rows([a], custom_fields=[])

        data = svc._render_xlsx(rows, column_names=list(rows[0].keys()))
        ws = self._load(data)["资产清单"]
        # 10 列 (固定) + 1 行 header + 1 行 data → "A1:J2"
        assert ws.auto_filter.ref == "A1:J2"

    def test_status_cell_filled_with_status_hex(self, session: Session):
        type_svc = TypeService(session)
        asset_svc = AssetService(session)
        svc = ExportService(session, asset_svc, type_svc)

        t = type_svc.create_type(name="L", code_prefix="L", custom_fields=[])
        a = asset_svc.register(name="X", type_id=t.id, custom_data={})  # IDLE
        rows = svc._build_rows([a], custom_fields=[])

        data = svc._render_xlsx(rows, column_names=list(rows[0].keys()))
        ws = self._load(data)["资产清单"]
        # 状态列是固定第 4 列 (D), data 在 row 2
        status_cell = ws.cell(row=2, column=4)
        assert status_cell.value == "闲置"
        # PatternFill 验 fgColor.rgb 与 STATUS_HEX[IDLE] 一致
        assert status_cell.fill.fgColor.rgb == STATUS_HEX[AssetStatus.IDLE]

    def test_empty_rows_only_header(self, session: Session):
        type_svc = TypeService(session)
        asset_svc = AssetService(session)
        svc = ExportService(session, asset_svc, type_svc)

        column_names = [
            "资产编号", "名称", "类型", "状态", "保管人", "位置",
            "闲置天数", "入账日期", "铭牌编号", "备注",
        ]
        data = svc._render_xlsx([], column_names=column_names)
        ws = self._load(data)["资产清单"]
        # row 1 = header, row 2 = 空
        assert ws.cell(row=1, column=1).value == "资产编号"
        assert ws.cell(row=2, column=1).value is None

    def test_notes_column_wider(self, session: Session):
        """spec §B.3: notes 列宽 cap 60, 其他列 cap 50."""
        type_svc = TypeService(session)
        asset_svc = AssetService(session)
        svc = ExportService(session, asset_svc, type_svc)

        t = type_svc.create_type(name="L", code_prefix="L", custom_fields=[])
        # notes 长文本测试列宽自适应
        a = asset_svc.register(
            name="X", type_id=t.id, custom_data={},
            notes="x" * 100,  # 100 char 长文本, 列宽应 cap 60
        )
        rows = svc._build_rows([a], custom_fields=[])

        data = svc._render_xlsx(rows, column_names=list(rows[0].keys()))
        ws = self._load(data)["资产清单"]
        # 备注是固定第 10 列 (J)
        assert ws.column_dimensions["J"].width is not None
        assert ws.column_dimensions["J"].width <= 60

    def test_wrap_text_enabled(self, session: Session):
        type_svc = TypeService(session)
        asset_svc = AssetService(session)
        svc = ExportService(session, asset_svc, type_svc)

        t = type_svc.create_type(name="L", code_prefix="L", custom_fields=[])
        a = asset_svc.register(name="X", type_id=t.id, custom_data={}, notes="long text")
        rows = svc._build_rows([a], custom_fields=[])

        data = svc._render_xlsx(rows, column_names=list(rows[0].keys()))
        ws = self._load(data)["资产清单"]
        # data row 备注 cell wrap_text True
        notes_cell = ws.cell(row=2, column=10)
        assert notes_cell.alignment.wrap_text is True
```

- [ ] **Step 6.2: 跑测试(应失败)**

```bash
uv run pytest tests/unit/test_export_service.py::TestRenderXlsx -v
```

预期: FAIL — `_render_xlsx` 没实现.

- [ ] **Step 6.3: 实现 `_render_xlsx`**

`src/asset_hub/services/export.py` `ExportService` 内追加:

```python
    _SHEET_NAME = "资产清单"
    _STATUS_COLUMN_HEADER = "状态"
    _NOTES_COLUMN_HEADER = "备注"
    _COL_WIDTH_DEFAULT_CAP = 50
    _COL_WIDTH_NOTES_CAP = 60

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
        status_col_idx = column_names.index(self._STATUS_COLUMN_HEADER) + 1
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
        max_row = len(rows) + 1  # +1 for header
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
            # 取 header + 所有 data 单元格中最大字符数, 与 cap 取 min
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
```

文件顶部 import 段加:

```python
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
```

- [ ] **Step 6.4: 跑测试(应通过)**

```bash
uv run pytest tests/unit/test_export_service.py -v
```

预期: 28 PASS(Task 5 的 20 + 8 个 xlsx).

> **可能的失败模式**:
> - `auto_filter.ref` 期望 "A1:J2" 但 col 数与列名数对不上 → 看 `column_names` 长度
> - `cell.fill.fgColor.rgb` 是 ARGB 但 openpyxl 在某些版本可能默认存 sRGB 或别字段 → 改测试用 `start_color` / `fgColor.value` 或对比 `cell.fill.fill_type == "solid"` 兜底
> - 列宽 chinese char 算法(2x)是 heuristic, test 只验 cap, 不验精确值

- [ ] **Step 6.5: 提交**

```bash
git add src/asset_hub/services/export.py tests/unit/test_export_service.py
git commit -m "$(cat <<'EOF'
feat(export): _render_xlsx (openpyxl + 5 态 cell.fill + freeze + autofilter)

spec §B.7 / §B.7.1: sheet '资产清单' / row 1 bold header / freeze A2 /
auto_filter 全范围 / 状态列 PatternFill 按 STATUS_HEX 染色 /
列宽 cap (default 50, notes 60) + wrap_text=True.

中文字符列宽估算用 2x 启发式 (XLSX 列宽单位约等于英文字符).
EOF
)"
```

---

## Task 7: `export(format, **filter)` 整合 + filename(TDD)

**Files:**
- Modify: `src/asset_hub/services/export.py`
- Test: `tests/unit/test_export_service.py`

`export` 是 service 唯一对外方法.整合 list_assets + _resolve_custom_fields + _build_rows + _render_<format>,返 `(bytes, filename)`.

- [ ] **Step 7.1: 写测试**

`tests/unit/test_export_service.py` 追加:

```python
import re as _re


class TestExport:
    def test_format_csv_returns_bom_bytes(self, session: Session):
        type_svc = TypeService(session)
        asset_svc = AssetService(session)
        svc = ExportService(session, asset_svc, type_svc)

        t = type_svc.create_type(name="L", code_prefix="L", custom_fields=[])
        asset_svc.register(name="X", type_id=t.id, custom_data={})

        data, filename = svc.export(format="csv")
        assert data.startswith(b"\xef\xbb\xbf")
        assert filename.endswith(".csv")

    def test_format_xlsx_returns_pk_magic(self, session: Session):
        type_svc = TypeService(session)
        asset_svc = AssetService(session)
        svc = ExportService(session, asset_svc, type_svc)

        t = type_svc.create_type(name="L", code_prefix="L", custom_fields=[])
        asset_svc.register(name="X", type_id=t.id, custom_data={})

        data, filename = svc.export(format="xlsx")
        # XLSX 是 zip, magic bytes "PK\x03\x04"
        assert data.startswith(b"PK")
        assert filename.endswith(".xlsx")

    def test_filename_format(self, session: Session):
        type_svc = TypeService(session)
        asset_svc = AssetService(session)
        svc = ExportService(session, asset_svc, type_svc)

        _, filename = svc.export(format="csv")
        # spec §B.9: assets-YYYYMMDD-HHMM.csv
        assert _re.fullmatch(r"assets-\d{8}-\d{4}\.csv", filename), (
            f"unexpected filename: {filename!r}"
        )

    def test_filter_passed_through_to_list_assets(self, session: Session):
        """type_id 锁定 → 仅该 type 的 assets + custom_fields 平铺."""
        type_svc = TypeService(session)
        asset_svc = AssetService(session)
        svc = ExportService(session, asset_svc, type_svc)

        t1 = type_svc.create_type(
            name="Laptop", code_prefix="NB",
            custom_fields=[
                {"key": "sn", "label": "SN", "type": "string", "required": False},
            ],
        )
        t2 = type_svc.create_type(name="GPU", code_prefix="GPU", custom_fields=[])
        asset_svc.register(name="A1", type_id=t1.id, custom_data={"sn": "NB-001"})
        asset_svc.register(name="A2", type_id=t1.id, custom_data={"sn": "NB-002"})
        asset_svc.register(name="A3", type_id=t2.id, custom_data={})  # GPU

        data, _ = svc.export(format="csv", type_id=t1.id)
        text = data.decode("utf-8-sig")
        # 仅 t1 的 2 行 + 1 header = 3 行
        non_empty_lines = [l for l in text.splitlines() if l.strip()]
        assert len(non_empty_lines) == 3
        # 含 SN 平铺列
        assert "SN" in non_empty_lines[0]
        # 不含 GPU asset
        assert "A3" not in text

    def test_filter_no_type_id_no_custom_flatten(self, session: Session):
        type_svc = TypeService(session)
        asset_svc = AssetService(session)
        svc = ExportService(session, asset_svc, type_svc)

        t = type_svc.create_type(
            name="Laptop", code_prefix="NB",
            custom_fields=[
                {"key": "sn", "label": "SN", "type": "string", "required": False},
            ],
        )
        asset_svc.register(name="A1", type_id=t.id, custom_data={"sn": "NB-001"})

        data, _ = svc.export(format="csv")  # 不传 type_id
        text = data.decode("utf-8-sig")
        first_line = text.splitlines()[0]
        # SN 平铺列不应出现
        assert "SN" not in first_line

    def test_zero_results_csv_only_header(self, session: Session):
        type_svc = TypeService(session)
        asset_svc = AssetService(session)
        svc = ExportService(session, asset_svc, type_svc)

        # 完全空 db
        data, _ = svc.export(format="csv")
        text = data.decode("utf-8-sig")
        non_empty_lines = [l for l in text.splitlines() if l.strip()]
        assert len(non_empty_lines) == 1  # 仅 header
        assert non_empty_lines[0].startswith("资产编号,")
```

- [ ] **Step 7.2: 跑测试(应失败)**

```bash
uv run pytest tests/unit/test_export_service.py::TestExport -v
```

预期: FAIL — `export` 没实现.

- [ ] **Step 7.3: 实现 `export`**

`src/asset_hub/services/export.py` `ExportService` 内追加:

```python
    _FIXED_COLUMN_NAMES: list[str] = [
        "资产编号", "名称", "类型", "状态", "保管人", "位置",
        "闲置天数", "入账日期", "铭牌编号", "备注",
    ]

    def export(
        self,
        format: Literal["csv", "xlsx"],
        type_id: uuid.UUID | None = None,
        status: AssetStatus | None = None,
        holder: str | None = None,
        q: str | None = None,
        include_retired: bool = False,
        include_disposed: bool = False,
    ) -> tuple[bytes, str]:
        """spec §2.2: 整合 list_assets + 渲染. 返 (bytes, filename)."""
        assets = self.asset_service.list_assets(
            type_id=type_id,
            status=status,
            holder=holder,
            q=q,
            include_retired=include_retired,
            include_disposed=include_disposed,
            sort_by=None,
            sort_order="desc",
            limit=None,
            offset=None,
        )
        custom_fields = self._resolve_custom_fields(type_id)
        rows = self._build_rows(assets, custom_fields)

        column_names = list(self._FIXED_COLUMN_NAMES)
        for field in custom_fields:
            column_names.append(field.label or field.key)

        filename = self._build_filename(format)
        if format == "csv":
            return self._render_csv(rows, column_names=column_names), filename
        return self._render_xlsx(rows, column_names=column_names), filename

    @staticmethod
    def _build_filename(format: Literal["csv", "xlsx"]) -> str:
        """spec §B.9: assets-YYYYMMDD-HHMM.{csv,xlsx}."""
        stamp = datetime.now().strftime("%Y%m%d-%H%M")
        return f"assets-{stamp}.{format}"
```

文件顶部 import 段加:

```python
from datetime import datetime
```

- [ ] **Step 7.4: 跑测试(应通过)**

```bash
uv run pytest tests/unit/test_export_service.py -v
```

预期: 34 PASS(Task 6 的 28 + 6 个 export).

- [ ] **Step 7.5: 提交**

```bash
git add src/asset_hub/services/export.py tests/unit/test_export_service.py
git commit -m "$(cat <<'EOF'
feat(export): ExportService.export 整合 list_assets + 渲染 + filename

spec §2.2 公共 API: 接 format + 6 个 filter 参数, 内部调 list_assets
(sort/limit 强制 None, 整 filter 集导出); custom_fields 按 type_id
锁定决定平铺; 文件名 assets-YYYYMMDD-HHMM.{csv,xlsx}.
EOF
)"
```

---

## Task 8: `GET /api/export` router(TDD with `TestClient`)

**Files:**
- Create: `src/asset_hub/api/routers/export.py`
- Modify: `src/asset_hub/api/app.py`(register router)
- Test: `tests/api/test_export_routes.py`

- [ ] **Step 8.1: 看现有 router 注册模式**

```bash
grep -n "include_router\|from .routers" src/asset_hub/api/app.py 2>&1 | head -10
```

记录现有 router import + register 风格(routers/asset.py / type.py / stats.py 等),保持一致.

- [ ] **Step 8.2: 写 router 测试**

`tests/api/test_export_routes.py`(新文件):

```python
"""GET /api/export router 测试."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from asset_hub.models.asset import AssetStatus


class TestExportRoutes:
    def test_csv_200_with_bom_and_headers(self, client: TestClient, sample_assets):
        resp = client.get("/api/export?format=csv")
        assert resp.status_code == 200
        assert resp.content.startswith(b"\xef\xbb\xbf")
        assert resp.headers["content-type"].startswith("text/csv")
        cd = resp.headers["content-disposition"]
        assert "attachment" in cd
        assert cd.startswith('attachment; filename="assets-')
        assert cd.endswith('.csv"')

    def test_xlsx_200_with_pk_magic_and_headers(self, client: TestClient, sample_assets):
        resp = client.get("/api/export?format=xlsx")
        assert resp.status_code == 200
        assert resp.content.startswith(b"PK")
        assert resp.headers["content-type"].startswith(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        cd = resp.headers["content-disposition"]
        assert cd.endswith('.xlsx"')

    def test_missing_format_422(self, client: TestClient):
        resp = client.get("/api/export")
        assert resp.status_code == 422

    def test_invalid_format_422(self, client: TestClient):
        resp = client.get("/api/export?format=pdf")
        assert resp.status_code == 422

    def test_invalid_status_422(self, client: TestClient):
        resp = client.get("/api/export?format=csv&status=NOT_A_STATUS")
        assert resp.status_code == 422

    def test_filter_status_passed_through(self, client: TestClient, sample_assets):
        resp = client.get("/api/export?format=csv&status=IDLE")
        assert resp.status_code == 200
        text = resp.content.decode("utf-8-sig")
        # IDLE 资产只在状态列写"闲置"; 不会有"在用"
        assert "在用" not in text

    def test_filter_q_passed_through(self, client: TestClient, sample_assets):
        # sample_assets fixture 含 name 含 "Laptop" 的资产
        resp = client.get("/api/export?format=csv&q=Laptop")
        assert resp.status_code == 200

    def test_zero_results_returns_header_only(self, client: TestClient):
        # 空 db: db fixture 应每 test 重置
        resp = client.get("/api/export?format=csv")
        assert resp.status_code == 200
        text = resp.content.decode("utf-8-sig")
        non_empty = [l for l in text.splitlines() if l.strip()]
        assert len(non_empty) == 1
```

`sample_assets` fixture 在 `tests/api/conftest.py` 看现有 fixtures(M3a/M3b 应已落; 若没有同等 fixture, 看 `test_asset_routes.py` 怎么 register 资产, 同模式建一个 fixture).

最简 fallback:在 `tests/api/conftest.py` 加 fixture:

```python
@pytest.fixture
def sample_assets(client: TestClient, sample_type: dict):
    type_id = sample_type["id"]
    for name in ["Laptop-A", "Laptop-B", "Laptop-C"]:
        client.post("/api/assets", json={"name": name, "type_id": type_id, "custom_data": {}})
    yield
```

(`sample_type` 同样需要; 看现有 conftest 是否已有,没有则建一个 `client.post("/api/types", json={"name": "Laptop", "code_prefix": "NB", "custom_fields": []})`.)

- [ ] **Step 8.3: 跑测试(应失败)**

```bash
uv run pytest tests/api/test_export_routes.py -v
```

预期: 全 FAIL — router 没建.

- [ ] **Step 8.4: 写 router**

`src/asset_hub/api/routers/export.py`(新文件):

```python
"""GET /api/export router. spec §2.1."""
from __future__ import annotations

import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, Response

from asset_hub.api.deps import get_session
from asset_hub.models.asset import AssetStatus
from asset_hub.services.asset import AssetService
from asset_hub.services.export import ExportService
from asset_hub.services.type import TypeService

router = APIRouter(prefix="/api", tags=["export"])

_CONTENT_TYPES = {
    "csv": "text/csv; charset=utf-8",
    "xlsx": (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    ),
}


@router.get("/export")
def export_assets(
    session: Annotated[object, Depends(get_session)],
    format: Annotated[Literal["csv", "xlsx"], Query()],
    type_id: Annotated[uuid.UUID | None, Query()] = None,
    status: Annotated[AssetStatus | None, Query()] = None,
    holder: Annotated[str | None, Query()] = None,
    q: Annotated[str | None, Query()] = None,
    include_retired: Annotated[bool, Query()] = False,
    include_disposed: Annotated[bool, Query()] = False,
) -> Response:
    """spec §2.1: 单端点 CSV/XLSX 导出. format 必填; filter 复用 list."""
    asset_svc = AssetService(session)
    type_svc = TypeService(session)
    export_svc = ExportService(session, asset_svc, type_svc)

    data, filename = export_svc.export(
        format=format,
        type_id=type_id,
        status=status,
        holder=holder,
        q=q,
        include_retired=include_retired,
        include_disposed=include_disposed,
    )

    return Response(
        content=data,
        media_type=_CONTENT_TYPES[format],
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
```

> `get_session` dep 路径以项目实际为准 — 看 `src/asset_hub/api/routers/asset.py` 顶部 import.

- [ ] **Step 8.5: register router**

`src/asset_hub/api/app.py` 内,与现有 router register 风格一致追加:

```python
from asset_hub.api.routers import export as export_router  # 顶部 import
# ...
app.include_router(export_router.router)  # register 段
```

- [ ] **Step 8.6: 跑测试(应通过)**

```bash
uv run pytest tests/api/test_export_routes.py -v
```

预期: 8 PASS.

可能的修订点:
- `Content-Disposition` 在某些 starlette 版本可能 lowercase header → 改测试用 `.lower()` 兜底
- `sample_assets` fixture 命名以现有 conftest 为准(可能叫别的)
- `client` fixture 应已在 `tests/api/conftest.py`(M3a 落)

- [ ] **Step 8.7: 提交**

```bash
git add src/asset_hub/api/routers/export.py src/asset_hub/api/app.py tests/api/test_export_routes.py
git commit -m "$(cat <<'EOF'
feat(export): GET /api/export router

spec §2.1: 单端点 csv/xlsx 二选一, format 必填 (Literal 触发 422);
filter 复用 list (type_id/status/holder/q/include_retired/include_disposed),
不含 sort/limit/offset (整 filter 集导出);
Content-Type 与 Content-Disposition attachment header 按 format 设.
EOF
)"
```

---

## Task 9: 后端最终验证 + simplify pass

**Files:** 无新文件;视 simplify 反馈而定的小修

- [ ] **Step 9.1: ruff 全项目**

```bash
uv run ruff check .
```

预期: `All checks passed!`(M3b 后已是干净状态;若 export.py 有任何 ruff issue,在此修).

- [ ] **Step 9.2: pytest 全套**

```bash
uv run pytest -v
```

预期: 414(原)+ 34(unit/test_export_service)+ 8(api/test_export_routes)= **456 PASS**.若实际差,看是否新 fixture 与现有 conftest 冲突.

- [ ] **Step 9.3: simplify pass(派 3 reviewer)**

跑 `/simplify`(项目 skill).reviewer 关注:

- 复用: STATUS_LABELS 是否能立即让 stats CLI 等去字面量(spec §B.4 显式 follow-up,**本 PR 不做**,但 reviewer 可能提)
- 质量: `_render_xlsx` 是否过长可拆 helper(对照 plan 写法判断;若拆,确保所有测试仍 PASS)
- 效率: `_build_rows` for loop + 列宽 char count for 循环 — 单人项目 ≤500 行,不优化

**Controller 决策原则**: 严格按 task 范围范围;reviewer 提出"超范围 refactor"(如改 stats CLI / 重写 STATUS_HEX 转算 lib)记 follow-up,不在 PR-1 内做.

- [ ] **Step 9.4: 修任何 critical/important issue**

若 simplify 真有合理修订(如 `_render_xlsx` 中状态列染色逻辑可以提为 `_apply_status_fill(cell, status_label)` helper 让代码更清),做最小修订.commit message 用 `refactor(export):` 前缀.

- [ ] **Step 9.5: 最终全套验证**

```bash
uv run pytest -v
uv run ruff check .
```

预期: 全 PASS / 全绿.

- [ ] **Step 9.6: commit log 检查**

```bash
git log --oneline main..HEAD
```

预期 commit 顺序(每行精简):
1. `chore(deps): 加 openpyxl 3.1+ 依赖`
2. `feat(export): STATUS_LABELS + STATUS_HEX dict`
3. `feat(export): ExportService.__init__ + _resolve_custom_fields`
4. `feat(export): ExportService._build_rows`
5. `feat(export): _render_csv (UTF-8 BOM)`
6. `feat(export): _render_xlsx (openpyxl + 5 态 cell.fill)`
7. `feat(export): ExportService.export 整合 + filename`
8. `feat(export): GET /api/export router`
9. (可选)`refactor(export): simplify 反馈`

如顺序乱(基建在 router 之后),回看; M3a/M3b 都遵循 "service 早 → router 晚 → simplify 收尾" 模式.

---

## Task 10: PR-1 合并

**Files:** 无

- [ ] **Step 10.1: 切回 main + merge --no-ff**

```bash
git checkout main
git merge --no-ff feat/m3c-pr1-backend -m "Merge branch 'feat/m3c-pr1-backend' (M3c PR-1: CSV/XLSX 导出后端)"
git log --oneline -3
```

预期: HEAD 是 merge commit, parent[1] = `feat/m3c-pr1-backend` HEAD.

- [ ] **Step 10.2: 清本地分支**

```bash
git branch -d feat/m3c-pr1-backend
```

预期: `Deleted branch feat/m3c-pr1-backend (was <sha>)`.

PR-1 完结.PR-2 plan(前端)等本次合并后再起,以便基于真实 schema.d.ts 同步 + ExportService 实际签名.

---

## Self-Review Checklist

实施期完成 10 task 后跑:

- [ ] spec §B.1 决议(砍 CLI export)— PR-1 不建任何 CLI export 命令 ✓(本 plan 无 CLI task)
- [ ] spec §B.2 custom_data B 策略 — `_resolve_custom_fields` + `export()` 正确读 type_id 决定平铺
- [ ] spec §B.3 列方案 — 10 固定列严格按列序 + custom_fields 平铺
- [ ] spec §B.4 status 人类标签 — `STATUS_LABELS` dict + `_build_rows` 用它
- [ ] spec §B.5 中文 header
- [ ] spec §B.6 CSV UTF-8 BOM — `_render_csv` 字节前缀 `\xef\xbb\xbf`
- [ ] spec §B.7 + §B.7.1 XLSX — sheet "资产清单" / row 1 bold / freeze A2 / autofilter / 状态 PatternFill / 列宽 cap / wrap_text
- [ ] spec §B.9 时间戳 + 文件名 — `acquired_at` YYYY-MM-DD; filename `assets-YYYYMMDD-HHMM.{csv,xlsx}`
- [ ] spec §B.10 GET 不含 sort/limit/offset — `export()` hardcode `sort_by=None, limit=None, offset=None`
- [ ] spec §2.1 HTTP 422 — format 缺/非法 / status 非 5 态枚举都 422(FastAPI 自动 by Literal/Enum)
- [ ] 测试覆盖: service unit + router API
- [ ] PR commit 顺序合规
- [ ] STATUS_HEX 实际 hex 来自 oklch.com 算的真实值,不是占位
- [ ] ruff 全绿 / pytest 全 PASS

PR-1 合并即 M3c 后端就位,等 PR-2 前端接入.
