# M3c · CSV / XLSX 导出 设计

**日期**：2026-05-07  
**关联**：[M3 总览](./2026-05-03-m3-overview-design.md) §3.3  
**前置**：M3a (状态机基建) ✅ + M3b (看板) ✅ 已 ship；本里程碑串行接续

---

## 0. 范围

**包**：

- 后端 `GET /api/export?<filter>&format=csv|xlsx` 单端点
- ExportService（service 层唯一事实，复用 `AssetService.list_assets`）
- CSV：UTF-8 BOM + stdlib `csv.writer`
- XLSX：openpyxl + 5 态状态色 cell fill + 冻结首行 + autofilter + 列宽自适应（cap 50/60）
- 前端列表页"导出 ▾" DropdownMenu（Excel / CSV 二选一）
- 测试分层：service unit / API router / 前端 component

**不包**（明确 v2+ 或 YAGNI）：

- ❌ CLI `asset-hub export` —— **YAGNI**：Agent 已有 `asset list --json --type-id ... --status ...` 直接拿结构化数据，导出文件是人类工作流；CLI 一层重复劳动。修订 M3 总览 §3 表里"`asset-hub export` CLI 复用 service"那行
- ❌ Transition 历史 / 派出历史导出（M3 总览已锁不做）
- ❌ 自定义列选择
- ❌ 流式响应（单人项目 ~500 行 ceiling，XLSX < 200KB，一次性 OK）
- ❌ 0 结果时禁用按钮（前端复杂度成本不划算；后端正常返"仅 header"是合理回应）
- ❌ 前端 spinner / dialog confirm（直接下载 = 用户预期最快路径）
- ❌ custom_fields 全 type 并集宽表（多 type 时列爆炸；视觉灾难）
- ❌ Custom field type-aware formatter（v1 简化用 `str(value)`；v2 加 bool→是/否、date 格式化等）

## 1. 关键决策与理由

### B.1 · CLI export 砍掉

**决议**：M3c 不做 `asset-hub export` CLI。

**理由**：

1. CLI `asset-hub asset list --json --type-id <X> --status <Y> --limit 1000` 已落地（M2 落，M3a/M3b 完善），返标准 envelope `{success, data, metadata, error}`，data 含完整 `custom_data` JSON。Agent 直接消费结构化数据 —— 不需要先落 CSV/XLSX 再 parse
2. 项目定位（CLAUDE.md §"项目定位"）只服务两类：人类（GUI）+ Agent（CLI）。**导出 = 离线文件工作流 = 100% 人类语义**（发邮件 / 塞 SharePoint / 月度盘点档案）
3. 人类不会通过 CLI 触发导出（用 GUI 按钮）；Agent 不需要导出（已有 list --json）—— 没有第三类用户
4. cron 月底自动落盘 XLSX 在单人项目几乎用不到；如果未来有需求，再加 CLI（YAGNI 兜底）

**修订**：M3 总览 §3.3 段那行 `CLI asset-hub export 复用 service` 在本 spec 标记为"M3c 决议删除"。后续 SKILL.md（M3e）也无须提 export 命令。

### B.2 · custom_data 处理：B 策略（filter 锁定 type 时平铺）

**决议**：仅当 HTTP query `type_id` **显式锁定单一 type** 时，按 `type.custom_fields` 顺序平铺为列；不限 type 时不含 `custom_data`。

| 备选 | 拒绝理由 |
|---|---|
| A 不含 | 失去库存盘点最有价值字段（SN / CPU 型号 / 屏幕尺寸） |
| C 全部 type 字段并集（宽表） | 多 type (>5) 立刻爆列；同行其他 type 字段空着；视觉灾难 |
| D 单列 JSON 字符串 | 机器友好但人类盘点不友好；XLSX 失去"按列扫描"价值；export 不服务 Agent（B.1） |

**B 在 filter 不限 type 时退化为不含**——理由：用户 mental model 通常 "先 filter type → 再导出" 是天然动作；不限 type 时通常是混合查询，列爆炸 vs 列残缺都不优；选最干净的"只看固定列"。

**实现细节**：

- HTTP `type_id` 出现且为合法 UUID → ExportService 解析该 type 的 `custom_fields`，平铺
- HTTP `type_id` 缺失或非法 → 不平铺
- `q` 关键词搜索碰巧只命中单一 type 的资产 → **不平铺**（行为可预测优先于"智能猜测"）

### B.3 · 列方案：C + notes（10 固定 + custom_fields 平铺）

```
资产编号 | 名称 | 类型 | 状态 | 保管人 | 位置 | 闲置天数 | 入账日期 | 铭牌编号 | 备注 | [type.custom_fields.label...]
asset_code | name | type_name | status | holder | location | idle_days | acquired_at | serial_number | notes | <平铺>
```

| 备选 | 拒绝理由 |
|---|---|
| A 紧凑 8 列（无 SN / 无 notes） | SN 是盘点员肉眼对应实物的核心字段，缺它导出价值打折 |
| B 完整 12 列（含 notes / created_at / updated_at） | created_at / updated_at 对人类盘点意义低；Agent 需要全字段走 list --json |

**列宽**：notes cap = 60 chars；其他列 cap = 50 chars；都启 `wrap_text=True`（XLSX）

### B.4 · 状态字段值：人类标签

写 `"在用" / "闲置" / "维修中" / "已退役" / "已处置"`，**不写 enum 字面量**（IN_USE / IDLE / ...）。理由：export 不服务 re-import；人类用户读 XLSX 期望看自然语言。

**实现**：在 `src/asset_hub/services/export.py` 内落一份 `STATUS_LABELS: dict[AssetStatus, str]`。后续若 stats CLI 等其他模块也需要 backend status label 映射，可以在 simplify pass 把字面量统一指向此 dict（**不在 M3c 范围**，仅记录 follow-up）。

### B.5 · 列 header 语言：中文

中文（"资产编号" 等）。理由：用户 + 老板都是中文使用者；agent 不消费 export，列名给人看。custom_fields header 用 `field.label`（中文，与 GUI 列保持一致）。

### B.6 · CSV 编码：UTF-8 with BOM

stdlib `csv.writer` + 字节流前缀 `﻿`。理由：Excel 默认按 ANSI 解析 UTF-8 → 中文乱码硬伤；BOM 是行业 standard 兜底。Linux / Mac 文本编辑器对 BOM 透明。

### B.7 · XLSX 状态色：cell.fill PatternFill (5 hex hardcoded)

| 备选 | 拒绝理由 |
|---|---|
| Conditional formatting | 规则系统过重；每列定义繁；调试困难 |
| Emoji 前缀（🟢 / ⚪ / 🔧 / 🌙 / 📦） | 老 Excel / 黑白打印 emoji 渲染不可靠 |
| 不染色 | 5 态文字混在一列灰乎乎，扫描困难 |

**5 态 hex 来源**：实施期把 `frontend/src/styles/globals.css` light 模式 `--status-*` OKLCH 值用工具转 ARGB hex，落 dict 在 service 内。**与 GUI 视觉对齐但解耦**——XLSX 永远用 light hex（导出文件需打印友好，与浏览器 dark/light 切换无关）。

### B.7.1 · XLSX sheet 元信息

| 项 | 决策 |
|---|---|
| Sheet name | `"资产清单"` |
| Header row | row 1，bold |
| Freeze | `freeze_panes = "A2"` |
| Autofilter | `auto_filter.ref = full data range` |
| 列宽 | auto-fit cap 50 chars（notes 列 cap 60）；启 `wrap_text=True` |
| Row 1 之上元信息 | **不含**（不写 filter / 时间 / 总行数；纯数据便于 pivot/re-import） |

### B.8 · 前端 UX：DropdownMenu (A 方案)

单按钮 "导出 ▾" → Radix DropdownMenu 2 item ("Excel" / "CSV")。

| 备选 | 拒绝理由 |
|---|---|
| 单按钮 + confirm dialog | 多一层 ceremony；导出 = 一键拷数据语义下，dialog 是冗余仪式 |
| 双按钮 "导出 Excel" / "导出 CSV" | filter bar 视觉挤；已有"列显示" / "登记资产"按钮 |

**触发**：`window.location.href = buildExportUrl(search, format)`（原生下载，不用 fetch + blob）。理由：代码最简；浏览器 native 下载状态 / 错误处理足够。

**位置**：filter bar 右侧，与"列显示" / "登记资产"并排（具体并排顺序由实施期视觉调整）。

**0 结果**：后端正常返"仅 header"文件，前端**不禁用按钮**。理由：用户在 list 已能看到 empty state；如果还点导出，给一份"仅 header"是合理回应；前端禁用增加复杂度（要 wire `query.data.length`）。

**loading state**：不显示前端 spinner。XLSX 渲染 < 1s（500 行 ceiling），浏览器 native 下载状态足够。

**错误**：HTTP 4xx/5xx 让浏览器 native 显示下载失败；前端不拦截。

### B.9 · 时间戳与文件名

- `acquired_at` 写 `YYYY-MM-DD`（schema 已是 `date` 而非 `datetime`，无需 strftime）
- 文件名：`assets-YYYYMMDD-HHMM.{csv,xlsx}` —— 时间戳含分钟解决"同一天导多次"覆盖；用户下载夹按时间排序自然
- HTTP `Content-Disposition: attachment; filename="..."`（不用 `filename*=UTF-8''...` URL encoding，文件名全 ASCII）

### B.10 · filter 透传：GET query string

`GET /api/export` 复用 list filter schema（`type_id` / `status` / `holder` / `q` / `include_retired` / `include_disposed`），加 `format` 必填。**不含 `sort_by` / `sort_order` / `limit` / `offset`**（v1 export 整个 filter 集，不分页）。

GET 而非 POST：filter ≤6 字段 + q 短字符串 → URL 长度无忧；GET 与"用户复制 URL 重发同一份导出"语义一致。

## 2. 后端契约

### 2.1 HTTP 端点

```
GET /api/export
  Query:
    format: Literal["csv", "xlsx"]   # 必填
    type_id?: UUID
    status?: AssetStatus
    holder?: str
    q?: str
    include_retired?: bool = false
    include_disposed?: bool = false

→ 200 OK
   Content-Type:
     csv  → "text/csv; charset=utf-8"
     xlsx → "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
   Content-Disposition: attachment; filename="assets-YYYYMMDD-HHMM.{csv,xlsx}"
   <bytes>

→ 422  format 缺失或非法 / type_id 非合法 UUID / status 不在 5 态枚举
→ 500  openpyxl 渲染异常 / DB 异常（FastAPI default error mapping）
```

**异常映射**遵循项目 §3.5 集中策略（`api/app.py`）：`ValidationError` → 422；router 不写 try/except。

### 2.2 ExportService 签名

```python
# src/asset_hub/services/export.py

from typing import Literal

class ExportService:
    def __init__(self, session: Session, asset_service: AssetService, type_service: TypeService):
        ...

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
        """返 (file_bytes, suggested_filename)."""
        assets = self.asset_service.list_assets(
            type_id=type_id, status=status, holder=holder, q=q,
            include_retired=include_retired, include_disposed=include_disposed,
            sort_by=None, limit=None, offset=None,
        )
        custom_fields = self._resolve_custom_fields(type_id)  # B.2 strategy
        rows = self._build_rows(assets, custom_fields)
        if format == "csv":
            return self._render_csv(rows), self._filename("csv")
        return self._render_xlsx(rows), self._filename("xlsx")
```

**`_build_rows(assets, custom_fields)` 返**：`list[dict[str, str]]`，dict key 是中文 header，value 是已格式化字符串（status 已映射 label，date 已 isoformat，custom_field 用 `str()` 兜底）。

**`_render_csv(rows)` 返 bytes**：UTF-8 BOM + csv.writer。

**`_render_xlsx(rows)` 返 bytes**：openpyxl Workbook → BytesIO → bytes。状态列用 `PatternFill(start_color=hex, end_color=hex, fill_type="solid")`。

### 2.3 STATUS_LABELS / STATUS_HEX dict

```python
# src/asset_hub/services/export.py

STATUS_LABELS: dict[AssetStatus, str] = {
    AssetStatus.IN_USE: "在用",
    AssetStatus.IDLE: "闲置",
    AssetStatus.MAINTENANCE: "维修中",
    AssetStatus.RETIRED: "已退役",
    AssetStatus.DISPOSED: "已处置",
}

# B.7 决议：light 模式 OKLCH 转 ARGB hex（实施期算）
STATUS_HEX: dict[AssetStatus, str] = {
    AssetStatus.IN_USE: "FF<hex>",       # --status-in-use 转
    AssetStatus.IDLE: "FF<hex>",
    AssetStatus.MAINTENANCE: "FF<hex>",
    AssetStatus.RETIRED: "FF<hex>",
    AssetStatus.DISPOSED: "FF<hex>",
}
```

**OKLCH → ARGB hex 转换**：实施期用 Python culori-style lib 或在线工具（一次性，落值不动）。

## 3. 前端契约

### 3.1 ExportButton 组件

```tsx
// frontend/src/features/assets/list/export-button.tsx

import type { AssetsSearch } from "./search-schema";

interface Props {
  search: AssetsSearch;
}

export function ExportButton({ search }: Props) {
  // Radix DropdownMenu:
  //   trigger: <Button variant="outline" size="sm">导出 <ChevronDown /></Button>
  //   items: [
  //     { label: "Excel", onSelect: () => triggerDownload(search, "xlsx") },
  //     { label: "CSV",   onSelect: () => triggerDownload(search, "csv") },
  //   ]
}

function triggerDownload(search: AssetsSearch, format: "csv" | "xlsx") {
  window.location.href = buildExportUrl(search, format);
}

function buildExportUrl(search: AssetsSearch, format: "csv" | "xlsx"): string {
  // 仅传 filter 字段，不传 sort/page/pageSize
  const params = new URLSearchParams({ format });
  if (search.type) params.set("type_id", search.type);
  if (search.status) params.set("status", search.status);
  if (search.holder) params.set("holder", search.holder);
  if (search.q) params.set("q", search.q);
  if (search.show_retired) params.set("include_retired", "true");
  if (search.show_disposed) params.set("include_disposed", "true");
  return `/api/export?${params.toString()}`;
}
```

注：`AssetsSearch` 现有 `show_retired` / `show_disposed`，后端 `/api/export` 用 `include_retired` / `include_disposed`（与 list / stats 一致）。`buildExportUrl` 做名字翻译。

### 3.2 接入 routes/index.tsx

filter bar 右侧"操作"区追加 `<ExportButton search={search} />`，与 `<ColumnVisibilityMenu />` / `<Link to="/assets/new">登记资产</Link>` 并排。

## 4. 测试分层

| 层 | 文件 | 覆盖 |
|---|---|---|
| Service unit | `tests/unit/test_export_service.py` | filter 透传 / 列序 / status 映射 / CSV BOM 字节 / 0 结果 仅 header / type_id 锁定时 custom_fields 平铺 / type_id 缺失时不平铺 / acquired_at 格式 |
| XLSX 内部 | `tests/unit/test_export_service.py` 同文件 | openpyxl 读回验 sheet 名 / freeze_panes / auto_filter / 状态列 cell.fill rgb 与 5 态 hex 对齐 |
| Router API | `tests/api/test_export_routes.py` | HTTP filter 解析 / 422 缺 format / 422 非法 status / Content-Type / Content-Disposition filename 形态 |
| 前端 component | `frontend/tests/components/export-button.test.tsx` | DropdownMenu 行为 / URL build (含/不含 filter 字段) / show_retired → include_retired 翻译 / format 切换 |

不写 e2e（M3e 统一）。

## 5. 依赖

新增：

```toml
# pyproject.toml [project] dependencies 追加
"openpyxl>=3.1",
```

前端：复用现有 `@radix-ui/react-dropdown-menu`（已装，types-table / theme-toggle 用过）。

## 6. PR 拆分

| PR | 范围 | 关键文件 |
|---|---|---|
| **PR-1 后端** | ExportService + router + 测试 + openpyxl 依赖 | `src/asset_hub/services/export.py`, `src/asset_hub/api/routers/export.py`, `tests/{unit,api}/test_export*.py`, `pyproject.toml` |
| **PR-2 前端** | ExportButton + filter bar 接入 + 测试 + schema 同步 | `frontend/src/features/assets/list/export-button.tsx`, `frontend/src/routes/index.tsx`, `frontend/tests/components/export-button.test.tsx`, `pnpm gen:api` 同步 schema |

PR-2 起前先合 PR-1，与 M3a/M3b 串行节奏一致。

## 7. 实施期占位（spec 实施期补）

下列内容 brainstorm 阶段无法定，留 PR-1/PR-2 实施期用 commit message + simplify pass 补：

- 5 态 hex 实际值（OKLCH 转算）
- ExportButton 与 ColumnVisibilityMenu / "登记资产" 在 filter bar 的具体并排顺序
- Playwright MCP 烟测场景（PR-2 验收期补）
