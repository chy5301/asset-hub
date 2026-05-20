# M4 · 视觉打磨主 PR Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 单个 M4 PR 内消化 6 个子项：A) `useFormDialog` 抽 checkout/return-dialog 样板 / B) 配色精打磨 5 修复点 / C) 看板可用性（#13） / D) lightbox 大屏宽度修（#14） / E) 列表排序（#15） / F) asset-header flaky 测试修。发版 v2.2.0。

**Architecture:** 严格 P 幅度（spec 决策）—— 不动 MASTER.md 整体色板，仅修具体问题点。所有改动仅前端 + 1 处后端 schema（M4-C IdleTopItem 加 name）。无 db migration。无 CLI 改动。

**Tech Stack:** React + RHF + Zod + TanStack Table + shadcn/ui Dialog + Recharts + Tailwind + Vitest。

**Spec 来源**：`docs/superpowers/specs/2026-05-17-m4-batch-plan-design.md` M4 主 PR 段。
**先决条件**：v2.1.0 已发布（CL-1 brand 升顶层已合并）。
**预期开销**：单 PR / 7 phase / ~15 task / commit 主干约 6-8 条。SemVer MINOR。

---

## Phase 1：M4-C 后端 - IdleTopItem 加 name + stats query

### Task 1.1：写后端 schema 测试

**Files:**

- Modify: `D:\CONGHAOYANG\Projects\tools\asset-hub\tests\unit\test_stats_service.py`（如不存在则 `Create`）

- [ ] **Step 1：写测试**

```python
def test_idle_top_includes_asset_name(session, idle_asset_fixture):
    """_idle_top 应返回 IdleTopItem 含 asset_name 字段。"""
    from asset_hub.services.stats import StatsService

    svc = StatsService(session)
    top = svc._idle_top(limit=10)
    assert len(top) > 0
    item = top[0]
    assert hasattr(item, "name")  # 新字段
    assert item.name is not None
    assert isinstance(item.name, str)


def test_stats_dashboard_endpoint_returns_idle_top_with_name(client, idle_asset_fixture):
    """GET /api/stats/dashboard idle_top 数组每项应含 name 字段。"""
    resp = client.get("/api/stats/dashboard")
    assert resp.status_code == 200
    data = resp.json()
    assert "idle_top" in data
    assert len(data["idle_top"]) > 0
    for item in data["idle_top"]:
        assert "name" in item
        assert isinstance(item["name"], str)
```

- [ ] **Step 2：跑测试看 fail**

```bash
uv run pytest tests/unit/test_stats_service.py tests/api/test_stats_routes.py -v -k name
```

期望 FAIL（IdleTopItem 缺 name 字段）。

### Task 1.2：实现 schema + query

**Files:**

- Modify: `D:\CONGHAOYANG\Projects\tools\asset-hub\src\asset_hub\api\schemas\stats.py`
- Modify: `D:\CONGHAOYANG\Projects\tools\asset-hub\src\asset_hub\services\stats.py`

- [ ] **Step 1：`IdleTopItem` 加 name 字段**

`api/schemas/stats.py` 行 32-39：

```python
class IdleTopItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    asset_id: UUID
    asset_code: str
    name: str   # M4-C 新增（紧贴 asset_code 之后）
    type_name: str | None
    current_location: str | None
    idle_days: int
    idle_since: UtcDatetime
```

- [ ] **Step 2：`_idle_top` query select Asset.name**

`services/stats.py` 行 137-165：

```python
def _idle_top(self, limit: int) -> list[IdleTopItem]:
    sq = last_idle_subq()
    idle_since = idle_since_expr(Asset, subq=sq)
    stmt = (
        select(
            Asset.id, Asset.asset_code, Asset.name,  # M4-C 加 Asset.name
            AssetType.name.label("type_name"), Asset.location, idle_since
        )
        .join(AssetType, AssetType.id == Asset.type_id)
        .outerjoin(sq, sq.c.asset_id == Asset.id)
        .where(Asset.status == AssetStatus.IDLE)
        .order_by(idle_since.asc())
        .limit(limit)
    )
    now = datetime.now(UTC)
    items = []
    for aid, code, name, type_name, location, since in self.session.exec(stmt).all():  # 加 name 解包
        since_aware = ensure_aware(since)
        days = int((now - since_aware).total_seconds() // 86400)
        items.append(
            IdleTopItem(
                asset_id=aid,
                asset_code=code,
                name=name,   # M4-C 新增
                type_name=type_name,
                current_location=location,
                idle_days=days,
                idle_since=since_aware,
            )
        )
    return items
```

**注意**：原 query 用 `AssetType.name` 但不带 label——SQL 层无歧义但 Python row 解包时和 `Asset.name` 会冲突。加 `.label("type_name")` 显式区分（如果原来已 OK，保持原状）。

- [ ] **Step 3：跑测试看 pass**

```bash
uv run pytest tests/unit/test_stats_service.py tests/api/test_stats_routes.py -v -k name
```

期望 PASS。

- [ ] **Step 4：跑全后端测**

```bash
uv run pytest -v
```

期望全绿。

- [ ] **Step 5：跑 gen:api 同步**

```bash
uv run uvicorn asset_hub.api.app:app --port 8000 &
sleep 2
pnpm --dir frontend gen:api
kill %1
```

期望 `frontend/src/api/generated/schema.d.ts` 中 `IdleTopItem` 新增 `name: string`。

- [ ] **Step 6：commit**

```bash
git add src/asset_hub/api/schemas/stats.py src/asset_hub/services/stats.py tests/ frontend/src/api/generated/schema.d.ts
git commit -m "feat(stats): IdleTopItem 加 name 字段 + gen:api 同步

M4-C 后端部分：闲置 Top API 返回值含资产名，看板 Y 轴可显示有意义 label 而非 asset_code。"
```

---

## Phase 2：M4-C 前端 - 看板 Y 轴改 name + 排版

### Task 2.1：Y 轴 dataKey 改 name

**Files:**

- Modify: `D:\CONGHAOYANG\Projects\tools\asset-hub\frontend\src\features\dashboard\charts\idle-top-bar-chart.tsx`（行 48-55）

- [ ] **Step 1：修改 Y 轴 dataKey**

行 48-55 当前：

```tsx
<YAxis
  type="category"
  dataKey="asset_code"
  tickLine={false}
  axisLine={false}
  tick={{ fill: "var(--foreground)", fontSize: 11 }}
  width={90}
/>
```

改为：

```tsx
<YAxis
  type="category"
  dataKey="name"   // M4-C：用资产名替代 asset_code，asset_code 在 tooltip 显示
  tickLine={false}
  axisLine={false}
  tick={{ fill: "var(--foreground)", fontSize: 11 }}
  width={140}   // 名称比 asset_code 通常更长，加宽
/>
```

- [ ] **Step 2：Tooltip 加 asset_code 作辅助信息**

行 87-110 `IdleTooltip` 当前：

```tsx
<div className="rounded-md border bg-popover px-3 py-2 shadow-md text-xs space-y-1">
  <div className="font-medium">{item.asset_code}</div>
  <div className="text-muted-foreground">{item.type_name}</div>
  ...
</div>
```

改为：

```tsx
<div className="rounded-md border bg-popover px-3 py-2 shadow-md text-xs space-y-1">
  <div className="font-medium">{item.name}</div>
  <div className="text-muted-foreground">{item.asset_code} · {item.type_name}</div>
  ...
</div>
```

- [ ] **Step 3：看板排版按 MASTER spacing token 强约束收口**

```bash
grep -n "dashboard-page\|dashboard-header" frontend/src/features/dashboard/
```

定位 `dashboard-page.tsx` 和 `dashboard-header.tsx` 文件。**不要"目测视觉收敛"，按下面强 token 约束做**：

- 卡片间距统一 `gap-6`（24px = MASTER `--space-lg`）
- 卡片内 padding 统一 `p-6`（24px = `--space-lg`）
- 栅格：`grid grid-cols-12` + 4 个 chart 卡片均 `col-span-6`（2x2 布局，不允许 5/7/8 等不规则）
- 看板 H1 用 `text-3xl font-medium tracking-tight`（MASTER §排版 type scale M3d 引入已锁定）
- 卡片背景割裂（spec M4-B #1）：**Phase 7 用 dashboard atmosphere token 处理**（见 Phase 7 Task 7.1），不在本 task 改

每改一处跑 dev server 验证 spacing 一致；超出上述 token 的间距需在 commit msg 注明理由。

- [ ] **Step 4：单测**

如有 `idle-top-bar-chart.test.tsx`，跑：

```bash
pnpm --dir frontend test idle-top-bar-chart
```

无则跳过（推迟到 Task 2.2 加测）。

- [ ] **Step 5：commit**

```bash
git add frontend/src/features/dashboard/
git commit -m "feat(dashboard): 闲置 Top 图 Y 轴用资产名而非编号 + 排版微调

M4-C 前端：
- idle-top-bar-chart Y 轴 dataKey: asset_code → name，width 90 → 140
- Tooltip 主标题用 name，副标题用 asset_code · type_name
- dashboard 卡片间距 / 栅格对齐微调（详见 diff）"
```

---

## Phase 3：M4-E 列表排序（type / status）

### Task 3.1：写 sortingFn 单测

**Files:**

- Create: `D:\CONGHAOYANG\Projects\tools\asset-hub\frontend\tests\unit\assets-table-sorting.test.ts`

- [ ] **Step 1：写测试**

```typescript
import { describe, it, expect } from "vitest";
import { statusSortingFn } from "@/features/assets/list/assets-table-sorting";

describe("statusSortingFn", () => {
  it("应按 ASSET_STATUS_VALUES 生命周期顺序排序", () => {
    // ASSET_STATUS_VALUES = ["IDLE", "IN_USE", "MAINTENANCE", "BROKEN", "RETIRED", "DISPOSED"]
    const rowA = { original: { status: "DISPOSED" } } as any;
    const rowB = { original: { status: "IDLE" } } as any;
    const rowC = { original: { status: "BROKEN" } } as any;

    expect(statusSortingFn(rowA, rowB, "status")).toBeGreaterThan(0);   // DISPOSED > IDLE
    expect(statusSortingFn(rowB, rowC, "status")).toBeLessThan(0);      // IDLE < BROKEN
    expect(statusSortingFn(rowB, rowB, "status")).toBe(0);              // 同状态返 0
  });

  it("未知状态应返 0 不抛错（防 schema 漂移）", () => {
    const rowA = { original: { status: "WEIRD_STATUS" as any } } as any;
    const rowB = { original: { status: "IDLE" } } as any;
    expect(statusSortingFn(rowA, rowB, "status")).toBe(0);
  });
});
```

- [ ] **Step 2：跑 test 看 fail**

```bash
pnpm --dir frontend test assets-table-sorting
```

期望 FAIL（`statusSortingFn` 未定义 / 模块不存在）。

### Task 3.2：实现 sortingFn + 改 ColumnDef

**Files:**

- Create: `D:\CONGHAOYANG\Projects\tools\asset-hub\frontend\src\features\assets\list\assets-table-sorting.ts`
- Modify: `D:\CONGHAOYANG\Projects\tools\asset-hub\frontend\src\features\assets\list\assets-table.tsx`（行 122-138）

- [ ] **Step 1：抽 sortingFn 到独立文件**

```typescript
// frontend/src/features/assets/list/assets-table-sorting.ts
import type { Row } from "@tanstack/react-table";

import { ASSET_STATUS_VALUES } from "./search-schema";
import type { AssetRow } from "@/features/assets/types";

/**
 * status 列按 ASSET_STATUS_VALUES 数组下标排序（生命周期顺序），
 * 未知状态返 0 防 schema 漂移导致排序抛错。
 */
export function statusSortingFn(
  rowA: Row<AssetRow>,
  rowB: Row<AssetRow>,
  _columnId: string,
): number {
  const a = ASSET_STATUS_VALUES.indexOf(rowA.original.status as never);
  const b = ASSET_STATUS_VALUES.indexOf(rowB.original.status as never);
  if (a < 0 || b < 0) return 0;
  return a - b;
}
```

- [ ] **Step 2：改 `assets-table.tsx` 的 type 和 status 列**

行 122-130（type 列）：删 `enableSorting: false`：

```typescript
{
  id: "type",
  accessorFn: (r) => r.type_name ?? "",
  header: COLUMN_LABELS.type,
  // enableSorting: false,   ← 删
  cell: ({ row }) => (
    <span className="text-sm text-muted-foreground">
      {row.original.type_name ?? "—"}
    </span>
  ),
},
```

行 132-138（status 列）：删 `enableSorting: false` + 加 `sortingFn`：

```typescript
import { statusSortingFn } from "./assets-table-sorting";

// ...

{
  id: "status",
  accessorKey: "status",
  header: COLUMN_LABELS.status,
  // enableSorting: false,   ← 删
  sortingFn: statusSortingFn,   // M4-E 新增
  cell: ({ row }) => <StatusBadge status={row.original.status} />,
},
```

- [ ] **Step 3：跑 test 看 pass**

```bash
pnpm --dir frontend test assets-table-sorting
```

期望 PASS。

### Task 3.3：加 e2e spec 防回归

**Files:**

- Create: `D:\CONGHAOYANG\Projects\tools\asset-hub\frontend\e2e\specs\list-sort-by-type-status.spec.ts`

- [ ] **Step 1：写 e2e spec**

```typescript
import { test, expect } from "@playwright/test";

test.describe("资产列表 - 类型/状态列排序", () => {
  test("点击类型列表头应触发字典序升序", async ({ page }) => {
    await page.goto("/");
    const typeHeader = page.getByRole("columnheader", { name: /类型/ });
    await typeHeader.click();
    // 期望 URL 含 ?sort=type
    await expect(page).toHaveURL(/sort=type/);
  });

  test("点击状态列表头应按生命周期顺序排序，IDLE 排第一", async ({ page }) => {
    await page.goto("/");
    const statusHeader = page.getByRole("columnheader", { name: /状态/ });
    await statusHeader.click();
    await expect(page).toHaveURL(/sort=status/);
    // 第一行应是闲置中（IDLE 在 ASSET_STATUS_VALUES 第 0 位）
    const firstRow = page.locator("tbody tr").first();
    await expect(firstRow).toContainText("闲置中");
  });
});
```

- [ ] **Step 2：跑 e2e（本地）**

```bash
pnpm --dir frontend exec playwright test list-sort-by-type-status
```

期望 PASS（如本机 e2e 环境 OK；CI 会跑）。

- [ ] **Step 3：用 Playwright MCP 烟测排序图标三态视觉**

承接 MASTER §M3a 烟测发现的"列表 Toggle pressed 视觉态较弱"同源风险 —— 排序图标 active 态视觉也要校：

- `browser_navigate` → `http://localhost:5173/`
- `browser_click` type 列表头：图标应变 `ArrowUp`（升序），与其他列已有图标视觉一致
- 再 `browser_click` → 图标变 `ArrowDown`（降序）
- 再 `browser_click` → 图标变 `ArrowUpDown`（清除排序，回中性）
- 三态视觉差异**应清晰**（不要像 M3a Toggle pressed 那样视觉太弱）

如三态视觉差异不够，加 weight：升降序态用 `text-foreground`，中性态用 `text-muted-foreground/50`。

- [ ] **Step 4：commit**

```bash
git add frontend/src/features/assets/list/ frontend/tests/unit/assets-table-sorting.test.ts frontend/e2e/specs/list-sort-by-type-status.spec.ts
git commit -m "feat(list): 类型和状态列支持排序（生命周期序）

M4-E：
- 抽 statusSortingFn 到 assets-table-sorting.ts，按 ASSET_STATUS_VALUES 下标排序
- assets-table.tsx 删 type / status 两列的 enableSorting: false
- status 列加 sortingFn={statusSortingFn}
- unit test 覆盖 sortingFn + 未知状态兜底
- 加 e2e spec 防 enableSorting 误改回 false 回归
- Playwright MCP 烟测排序图标三态视觉清晰（顺修 M3a Toggle pressed 视觉弱化风险）

闭环 issue #15。"
```

---

## Phase 4：M4-D lightbox

### Task 4.1：写 lightbox 失败测试

**Files:**

- Create: `D:\CONGHAOYANG\Projects\tools\asset-hub\frontend\tests\unit\attachment-lightbox.test.tsx`（如已存在则 Modify）

- [ ] **Step 1：写测试**

```typescript
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { AttachmentLightbox } from "@/features/assets/detail/attachment-lightbox";

// mock 必要 props
const mockAttachment = {
  id: "att-1",
  original_name: "test.png",
  mime_type: "image/png",
  size: 1024,
  sha256: "abc",
  uploaded_at: "2026-01-01T00:00:00Z",
};

describe("AttachmentLightbox", () => {
  it("DialogContent 应有 !max-w-[90vw] 覆盖 sm:max-w-sm 默认", () => {
    render(
      <AttachmentLightbox
        open={true}
        attachment={mockAttachment as any}
        onClose={() => {}}
      />,
    );
    const dialog = screen.getByRole("dialog");
    expect(dialog.className).toContain("!max-w-[90vw]");
  });

  it("应只渲染一个关闭按钮（自定义工具栏里的，不要 DialogContent 默认那个）", () => {
    render(
      <AttachmentLightbox
        open={true}
        attachment={mockAttachment as any}
        onClose={() => {}}
      />,
    );
    const closeButtons = screen.getAllByRole("button", { name: /关闭|Close/ });
    expect(closeButtons).toHaveLength(1);
  });
});
```

- [ ] **Step 2：跑 test 看 fail**

```bash
pnpm --dir frontend test attachment-lightbox
```

期望 FAIL（默认 `!max-w-` 不存在 + 双 X）。

### Task 4.2：实现 lightbox 修复

**Files:**

- Modify: `D:\CONGHAOYANG\Projects\tools\asset-hub\frontend\src\features\assets\detail\attachment-lightbox.tsx`（行 72-74）

- [ ] **Step 0：复查反 glassmorphism / AI-slop 红线**

```bash
grep -rnE 'scale-|animate-spin|backdrop-blur|bg-gradient-to' \
  frontend/src/features/assets/detail/attachment-lightbox.tsx \
  frontend/src/components/ui/dialog.tsx
```

期望 0 命中（shadcn skeleton 的 `animate-pulse` 是历史例外，不算）。

如发现 `backdrop-blur` 命中：MASTER §M2c-2 §1 已明确"Modal backdrop-filter: blur(4px) → bg-black/50 不 blur，glassmorphism overused" —— 必须改回 `bg-black/50` 不 blur。

另顺扫 `ZoomableImage` 组件实现（lightbox 内嵌）：

```bash
grep -rnE 'scale-|animate-spin|transform.*scale' frontend/src/features/assets/detail/zoomable-image.tsx
```

确认无 layout-shifting `scale` transform（MASTER 反 AI-slop 红线 #3）；如有则用 `cursor-zoom-in/out` + 真实尺寸切换替代。

- [ ] **Step 1：改 DialogContent props**

行 72-74 当前：

```tsx
<DialogContent
  className="max-w-[90vw] max-h-[90vh] p-0 overflow-hidden"
>
```

改为：

```tsx
<DialogContent
  className="!max-w-[90vw] max-h-[90vh] p-0 overflow-hidden"
  showCloseButton={false}
>
```

**说明**：

- `!max-w-[90vw]` 加 `!` important 前缀，tailwind-merge 覆盖 `dialog.tsx:62` 的 `sm:max-w-sm` 默认
- `showCloseButton={false}` 关闭 `dialog.tsx:51` 默认渲染的 X（保留自定义工具栏 X，spec 选方案 A）

- [ ] **Step 2：跑 test 看 pass**

```bash
pnpm --dir frontend test attachment-lightbox
```

期望 PASS。

- [ ] **Step 3：commit**

```bash
git add frontend/src/features/assets/detail/attachment-lightbox.tsx frontend/tests/unit/attachment-lightbox.test.tsx
git commit -m "fix(lightbox): 大屏宽度撑满 + 去重关闭按钮

M4-D：
- DialogContent className 加 !max-w-[90vw] important 覆盖 dialog.tsx:62 默认 sm:max-w-sm
  （tailwind-merge 不会自动覆盖不同响应式前缀）
- DialogContent showCloseButton={false} 关掉默认 X，保留自定义工具栏里的 X
- unit test 覆盖宽度类 + 单 X 渲染

闭环 issue #14。"
```

---

## Phase 5：M4-A useFormDialog 抽离

### Task 5.1：抽 useFormDialog hook + 写测试

**Files:**

- Create: `D:\CONGHAOYANG\Projects\tools\asset-hub\frontend\src\features\assets\detail\use-form-dialog.ts`
- Create: `D:\CONGHAOYANG\Projects\tools\asset-hub\frontend\tests\unit\use-form-dialog.test.ts`

- [ ] **Step 1：先写 hook 接口测试**

```typescript
// frontend/tests/unit/use-form-dialog.test.ts
import { describe, it, expect, vi } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { z } from "zod";
import { useFormDialog } from "@/features/assets/detail/use-form-dialog";

const schema = z.object({ value: z.string().min(1) });

describe("useFormDialog", () => {
  it("成功 submit 应调 mutate 并触发 onSuccess", async () => {
    const mutateMock = vi.fn().mockResolvedValue({});
    const onSuccessMock = vi.fn();
    const onOpenChange = vi.fn();

    const { result } = renderHook(() =>
      useFormDialog({
        schema,
        defaultValues: { value: "" },
        mutate: mutateMock,
        onSuccess: onSuccessMock,
        onOpenChange,
      }),
    );

    await act(async () => {
      result.current.form.setValue("value", "hello");
      await result.current.onSubmit({ value: "hello" });
    });

    expect(mutateMock).toHaveBeenCalledWith({ value: "hello" });
    expect(onSuccessMock).toHaveBeenCalled();
    expect(onOpenChange).toHaveBeenCalledWith(false);
  });

  it("失败 submit 应 setError('root') 不关 dialog", async () => {
    const mutateMock = vi.fn().mockRejectedValue(new Error("backend fail"));
    const onOpenChange = vi.fn();

    const { result } = renderHook(() =>
      useFormDialog({
        schema,
        defaultValues: { value: "" },
        mutate: mutateMock,
        onSuccess: vi.fn(),
        onOpenChange,
      }),
    );

    await act(async () => {
      await result.current.onSubmit({ value: "hello" });
    });

    expect(result.current.form.formState.errors.root).toBeDefined();
    expect(onOpenChange).not.toHaveBeenCalledWith(false);
  });
});
```

- [ ] **Step 2：跑 test 看 fail**

```bash
pnpm --dir frontend test use-form-dialog
```

期望 FAIL（模块不存在）。

- [ ] **Step 3：实现 hook**

```typescript
// frontend/src/features/assets/detail/use-form-dialog.ts
import { useForm, type DefaultValues, type Path } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import type { ZodSchema } from "zod";

import { toFriendlyMessage } from "@/lib/error";

interface UseFormDialogParams<T extends Record<string, unknown>> {
  schema: ZodSchema<T>;
  defaultValues: DefaultValues<T>;
  mutate: (values: T) => Promise<unknown>;
  onSuccess?: () => void;
  onOpenChange: (open: boolean) => void;
}

/**
 * M4-A：CheckoutDialog / ReturnDialog 共用的表单 dialog 样板：
 * useForm + zodResolver + onSubmit 含 toast & error 处理 + handleOpenChange。
 */
export function useFormDialog<T extends Record<string, unknown>>({
  schema,
  defaultValues,
  mutate,
  onSuccess,
  onOpenChange,
}: UseFormDialogParams<T>) {
  const form = useForm<T>({
    resolver: zodResolver(schema),
    defaultValues,
    mode: "onSubmit",
  });

  async function onSubmit(values: T) {
    try {
      await mutate(values);
      onSuccess?.();
      form.reset();
      onOpenChange(false);
    } catch (err) {
      form.setError("root" as Path<T>, { message: toFriendlyMessage(err) });
    }
  }

  function handleOpenChange(v: boolean, isPending: boolean) {
    if (isPending) return;
    if (!v) form.reset();
    onOpenChange(v);
  }

  return { form, onSubmit, handleOpenChange };
}
```

- [ ] **Step 4：跑 test 看 pass**

```bash
pnpm --dir frontend test use-form-dialog
```

期望 PASS。

### Task 5.2：refactor CheckoutDialog 用 useFormDialog

**Files:**

- Modify: `D:\CONGHAOYANG\Projects\tools\asset-hub\frontend\src\features\assets\detail\checkout-dialog.tsx`（共 239 行，spec scan 已贴）

- [ ] **Step 1：替换 useForm + handleOpenChange + onSubmit 三段为 useFormDialog**

替换 `checkout-dialog.tsx` 行 65-97 这段（含 useForm / handleOpenChange / onSubmit）：

```tsx
export function CheckoutDialog({
  open,
  onOpenChange,
  assetId,
  kind,
}: CheckoutDialogProps) {
  const meta = META[kind];
  const Icon = meta.Icon;
  const mutation = useRecordTransitionMutation(assetId);
  const { form, onSubmit, handleOpenChange } = useFormDialog<FormValues>({
    schema,
    defaultValues: { to_holder: "", to_location: "", note: "" },
    mutate: (values) =>
      mutation.mutateAsync({
        kind,
        to_holder: values.to_holder.trim(),
        to_location: values.to_location?.trim() || null,
        due_at: values.due_at ? `${values.due_at}T00:00:00` : null,
        note: values.note?.trim() || null,
      }),
    onSuccess: () => toast.success(`已${meta.verb}`),
    onOpenChange,
  });

  return (
    <Dialog open={open} onOpenChange={(v) => handleOpenChange(v, mutation.isPending)}>
      {/* ... DialogContent 内 form 部分不变 ... */}
    </Dialog>
  );
}
```

注意调整 import：

```tsx
import { useFormDialog } from "./use-form-dialog";
// 移除：import { useForm } from "react-hook-form";
// 移除：import { zodResolver } from "@hookform/resolvers/zod";
// 保留：import { toast } from "sonner";
// 保留：import { toFriendlyMessage } from "@/lib/error";  ← 现在 useFormDialog 已用，本文件可移除
```

- [ ] **Step 2：跑 CheckoutDialog 现有测试看通过**

```bash
pnpm --dir frontend test checkout-dialog
```

期望现有 2 case PASS（spec 提到 "tests/components/checkout-dialog.test.tsx 现有 2 case 保持绿"）。

### Task 5.3：refactor ReturnDialog 用 useFormDialog

**Files:**

- Modify: `D:\CONGHAOYANG\Projects\tools\asset-hub\frontend\src\features\assets\detail\return-dialog.tsx`（共 169 行）

- [ ] **Step 1：替换 ReturnDialog 同模式**

行 48-75 替换为：

```tsx
export function ReturnDialog({
  open,
  onOpenChange,
  assetId,
}: ReturnDialogProps) {
  const mutation = useRecordTransitionMutation(assetId);
  const { form, onSubmit, handleOpenChange } = useFormDialog<FormValues>({
    schema,
    defaultValues: { to_holder: "", to_location: "", note: "" },
    mutate: (values) =>
      mutation.mutateAsync({
        kind: "RETURN",
        to_holder: values.to_holder?.trim() || null,
        to_location: values.to_location?.trim() || null,
        note: values.note?.trim() || null,
      }),
    onSuccess: () => toast.success("已归还"),
    onOpenChange,
  });

  return (
    <Dialog open={open} onOpenChange={(v) => handleOpenChange(v, mutation.isPending)}>
      {/* ... DialogContent 内 form 部分不变 ... */}
    </Dialog>
  );
}
```

同样调整 import。

- [ ] **Step 2：跑 ReturnDialog 现有测试看通过**

```bash
pnpm --dir frontend test return-dialog
```

期望 PASS。

- [ ] **Step 3：跑 frontend 全测**

```bash
pnpm --dir frontend test
```

期望全绿（含 use-form-dialog 2 case + checkout-dialog 2 case + return-dialog 既有 case + 其他不变）。

- [ ] **Step 4：commit**

```bash
git add frontend/src/features/assets/detail/ frontend/tests/unit/use-form-dialog.test.ts
git commit -m "refactor(dialog): 抽 useFormDialog hook 收敛 checkout/return-dialog 样板

M4-A：
- 新 hook useFormDialog<T>({schema, defaultValues, mutate, onSuccess, onOpenChange})
  封装 useForm + zodResolver + onSubmit + handleOpenChange + try/setError('root')
- CheckoutDialog / ReturnDialog 各减 ~30 行样板
- 2 case unit test 覆盖 hook 成功 / 失败路径
- 现有 dialog 测试保持绿（外部行为零变化）"
```

---

## Phase 6：M4-F asset-header flaky test fix

### Task 6.1：fake timers 修 flaky

**Files:**

- Modify: `D:\CONGHAOYANG\Projects\tools\asset-hub\frontend\tests\components\asset-header.test.tsx`（行 224-226 附近）

- [ ] **Step 1：定位测试上下文**

```bash
grep -n "逾期 3 天\|逾期 \\\\d 天" frontend/tests/components/asset-header.test.tsx
```

定位行 200-230 区间的测试 case。

- [ ] **Step 2：用 vi.useFakeTimers 冻结时间**

修改测试，找到 `due_at = Date.now() - 3 * 86400000` 或类似构造，改为：

```typescript
import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";

// 在测试内或 beforeEach：
beforeEach(() => {
  vi.useFakeTimers();
  vi.setSystemTime(new Date("2026-01-15T12:00:00Z"));
});

afterEach(() => {
  vi.useRealTimers();
});

it("逾期 3 天显示正确文案", async () => {
  const dueAt = new Date("2026-01-12T12:00:00Z").toISOString();  // 3 天前
  render(<AssetHeader asset={{ ...mockAsset, due_at: dueAt }} />);
  expect(await screen.findByText("逾期 3 天")).toBeInTheDocument();
  expect(screen.queryByText(/逾期 8 天/)).not.toBeInTheDocument();
});
```

**关键**：

- `vi.setSystemTime` 固定到 `2026-01-15 UTC`
- `dueAt` 固定 ISO 时间戳 `2026-01-12 UTC`（差 3 天，时区无关）
- 不再用 `Date.now()` 减毫秒，因为这种构造在不同 timezone 上解析行为不一致

- [ ] **Step 3：跑测试看通过**

```bash
pnpm --dir frontend test asset-header
```

期望 PASS（fake timers 后无时区敏感性）。

- [ ] **Step 4：连跑 10 次确认无 flaky**

```bash
for i in 1 2 3 4 5 6 7 8 9 10; do pnpm --dir frontend test asset-header || break; done
```

期望 10 次全 PASS。

- [ ] **Step 5：commit**

```bash
git add frontend/tests/components/asset-header.test.tsx
git commit -m "fix(test): asset-header.test.tsx 逾期 3 天 flaky 用 fake timers 修

M4-F：根因 M3d commit 3dcdf56 引入 due_at = Date.now() - 3 * 86400000，
解析时无时区按 local 时间偏移得 3+ 天。改用 vi.useFakeTimers + vi.setSystemTime
固定到 2026-01-15 UTC，due_at 固定 ISO 时间戳——时区无关。"
```

---

## Phase 7：M4-B 配色精打磨 5 修复点

### Task 7.1：#13 看板背景割裂用 dashboard atmosphere token + filter toggle 文案统一

**Files:**

- Modify: dashboard route 根容器文件（具体定位见 Step 1）

**关键约束**：MASTER §Dashboard Atmosphere 早已定义专用 token：

```
--dashboard-bg-radial-from   /* radial gradient 起点 (顶部 50% 20%) */
--dashboard-bg-radial-to     /* radial gradient 终点 (向外铺) */
```

> "替代 solid 背景, light 模式偏白发光, dark 模式深蓝氛围."

**决策**：dashboard route 用该 token 实现专属 radial gradient 背景，dashboard 卡片保持 `bg-card`，radial 自然过渡消除色块割裂。**body 全局背景不动**（避免影响列表 / 详情 / 类型管理 3 页）。

- [ ] **Step 1：定位 dashboard route 根容器**

```bash
grep -rn "dashboard-bg-radial\|--dashboard-bg" frontend/src/
```

期望返：

- `frontend/src/index.css`（或 globals.css）含 token 定义（light + dark 两套）
- dashboard route 文件（如 `frontend/src/routes/dashboard.tsx` 或 `frontend/src/features/dashboard/dashboard-page.tsx`）—— 若 token **未在 JSX 应用**，本 task 即落地点

如 token 未在 JSX 应用，搜 dashboard route 入口：

```bash
ls frontend/src/routes/dashboard*
ls frontend/src/features/dashboard/dashboard-page.tsx
```

- [ ] **Step 2：在 dashboard route 根容器加 radial gradient**

在 dashboard route 最外层 wrapper 加 className（沿用 MASTER token 而非自定义 hex）：

```tsx
<div className="min-h-screen bg-[radial-gradient(50%_60%_at_50%_20%,var(--dashboard-bg-radial-from),var(--dashboard-bg-radial-to))]">
  {/* 原 dashboard 内容 */}
</div>
```

**说明**：

- 50%_60%_at_50%_20% 与 MASTER §Dashboard Atmosphere 注释"顶部 50% 20%"对齐
- 卡片保持 `bg-card`，与 radial gradient 自然过渡消除割裂
- light / dark 两套 token 已在 globals.css 落地，本 task 不动 token 定义

- [ ] **Step 3：filter toggle 文案统一**

`/dashboard` 顶部 toggle 当前文案"已退役 / 已注销"；`/`（列表）filter toggle 当前文案"显示退役 / 显示注销"。

```bash
grep -rn "已退役\|显示退役\|已注销\|显示注销" frontend/src/features/
```

定位两处，统一改为 "显示退役 / 显示注销"（spec 决策：与 STATUS_META label 配套更清晰）。

- [ ] **Step 4：本地视觉校对**

```bash
uv run asset-hub serve start --mode dev
```

打开 `http://localhost:5173/dashboard`、`/`、随机 `/assets/<id>` 详情，目测：

- dashboard 顶部有 radial gradient 微妙发光（light）/ 深蓝氛围（dark）
- dashboard 卡片不再有色块割裂（radial 平滑过渡到 bg-card）
- 列表与详情两页背景**完全未变化**（body 没动）
- 列表与 dashboard 的 toggle 文案一致

- [ ] **Step 2：filter toggle 文案统一**

`/dashboard` 顶部 toggle 当前文案"已退役 / 已注销"；`/`（列表）filter toggle 当前文案"显示退役 / 显示注销"。

```bash
grep -rn "已退役\|显示退役\|已注销\|显示注销" frontend/src/features/
```

定位两处，统一改为 "显示退役 / 显示注销"（spec 决策：与 STATUS_META label 配套更清晰）。

- [ ] **Step 3：本地视觉校对**

```bash
uv run asset-hub serve start --mode dev
```

打开 `http://localhost:5173/`、`/dashboard`、随机 `/assets/<id>` 详情，目测：

- dashboard 卡片不再有色块割裂
- 列表与 dashboard 的 toggle 文案一致
- 其他页面视觉无回归

### Task 7.2：toggle / chip 样式 + status 色 token 校准

**Files:**

- Modify: dashboard 与列表 filter toggle 组件 / 各 status badge 渲染处

**关键约束**：MASTER §M3a 实施期纠偏 §2 已实现「Toggle chip + status token 染色」模式：

> "列表 filter 区 '已退役' / '已处置' 两个独立 Toggle chip，按 status token 染色（off muted / on `bg-status-X/15` + `text-status-X-fg` + `border-status-X/30`）。视觉与 status pill 体系延续。URL 持久化。"

同时 §M3a 烟测 followup 已识别**遗留**：

> "列表 Toggle pressed 视觉态较弱（chip 在 on 时与 off 视觉差异不够明显）—— spec §5.10 review 时考虑加重 `data-[state=on]` 边框"

本 task 做两件事：(1) dashboard toggle 改用 M3a chip 模式与列表对齐；(2) 顺修 M3a pressed 视觉弱化遗留。

- [ ] **Step 1：dashboard toggle 改用 M3a Toggle chip + status token 染色模式**

```bash
grep -rn "bg-status-\|data-\[state=on\]" frontend/src/features/assets/list/
```

定位 M3a Toggle chip 实现位置（列表 filter 区）。然后 grep dashboard 当前 toggle：

```bash
grep -rn "toggle\|Toggle" frontend/src/features/dashboard/
```

dashboard 的 RETIRED / DISPOSED 显隐 toggle 走相同 chip pattern：

- off：`bg-muted text-muted-foreground border-transparent`
- on（已退役）：`bg-status-retired/15 text-status-retired-fg border-status-retired/30`
- on（已注销）：`bg-status-disposed/15 text-status-disposed-fg border-status-disposed/30`

两端 padding / border-radius / hover state 都用同一组 className。

- [ ] **Step 2：顺修 M3a pressed 视觉弱化遗留**

加重两端 chip 的 `data-[state=on]` 边框（或 ring）：

- 原：`border-status-X/30`
- 改：`border-status-X/60` 或加 `ring-1 ring-status-X/30`

**停止条件**：dashboard / 列表两端切换 on/off 时视觉差异**第一眼可见**（无需 pixel-peep）。

- [ ] **Step 3：status 色 token 对比度二次 verify（特别 BROKEN）**

MASTER §M2c-1 Pre-Delivery Checklist 已实测 light 模式 OKLCH 对比度 AA；本 task 仅做：

```bash
grep -rn "status-broken\|--status-broken" frontend/src/index.css design-system/
```

确认 BROKEN token 仍是 MASTER §status-broken 段约定的 light `oklch(0.93 0.13 30)` bg / `oklch(0.42 0.18 28)` fg（spec 锁定值），无人为调过。dark 模式做 spot check：

1. 打开 dev server，切 dark 模式
2. 用浏览器 DevTools 取 BROKEN badge 颜色值
3. 跑 WCAG contrast checker（https://webaim.org/resources/contrastchecker/）
4. 期望 ≥ 4.5:1（AA）

如未达标，按 MASTER §status-broken 段「dark `oklch(0.32 0.13 25)` bg / `oklch(0.82 0.15 30)` fg」回归即可。其他 5 态默认达标，不动。

- [ ] **Step 3：commit**

```bash
git add frontend/src/ design-system/
git commit -m "polish(design): 看板背景割裂 + filter toggle 文案统一 + status 色对比度校准

M4-B 修复点 1-4：
- 全局 body 背景 bg-background → bg-muted/30 让 dashboard 卡片 bg-card 视觉更协调
- dashboard / 列表 filter toggle 文案统一为「显示退役 / 显示注销」
- toggle / chip 组件样式收敛（padding / border-radius / hover state）
- status 色 token 6 态对比度校准至 WCAG AA（重点 BROKEN）"
```

### Task 7.3：空 / 错 / loading 态用公共组件统一（不重新拍样式）

**Files:**

- Modify: dashboard / 列表 / 详情 3 页的 empty / error / loading state 组件

**关键约束**：MASTER 已沉淀的公共组件（多轮纠偏成果），本 task **审计是否被复用**而非重新拍：

| 状态 | 公共组件 | 来源 |
|---|---|---|
| 空态 | `<EmptyState>` | M2c-1 H4 / TypesPage 接入 / 详情页 NotFoundPanel 抽出 |
| 404 / 资源不存在 | `<NotFoundPanel>` | M2 视觉收尾 H5 公共化 |
| loading | `<DetailSkeleton>` / `<GridSkeleton>` / `<TimelineSkeleton>` | M2c-1 / M2c-2 落地 |
| 错误（非 404）| `<ErrorState onRetry={refetch}>` | M2c-1 实施期默认引入 |

**反 AI-slop 红线**（MASTER §M2c-2 §1 + §M2c-3 §7 已明示）：

- **禁止 `animate-spin`**（spinner 是 AI-slop 重灾区）
- **禁止 `backdrop-blur`**（glassmorphism overused）
- **mutation pending → 按钮文字切换**（"派发中…" "归还中…"）
- **上传进度 → width transition**（不用 spinner）

- [ ] **Step 1：grep 3 页现状**

```bash
# 公共组件复用情况
grep -rn "EmptyState\|NotFoundPanel\|DetailSkeleton\|GridSkeleton\|TimelineSkeleton\|ErrorState" \
  frontend/src/features/dashboard/ \
  frontend/src/features/assets/list/ \
  frontend/src/features/assets/detail/

# 红线扫描（与历次纠偏一致）
grep -rnE 'scale-|animate-spin|backdrop-blur|bg-gradient-to' \
  frontend/src/features/dashboard/ \
  frontend/src/features/assets/list/ \
  frontend/src/features/assets/detail/
```

第二条预期：0 命中（shadcn skeleton 的 `animate-pulse` 是历史例外，不算）。如有命中**必须修**。

- [ ] **Step 2：列出 inline 实现 vs 公共组件对照表**

对每页（dashboard / 列表 / 详情）逐项确认：

```text
| 页 | 状态 | 当前实现 | 应改 |
|---|---|---|---|
| dashboard | empty | ? | <EmptyState> |
| dashboard | loading | ? | <GridSkeleton> 或同源 skeleton |
| dashboard | error | ? | <ErrorState onRetry={refetch}> |
| 列表 | empty | ? | <EmptyState>（M2c-1 H4 已接入） |
| 列表 | loading | ? | <GridSkeleton>（M2c-1 已接入） |
| 列表 | error | ? | <ErrorState> |
| 详情 | empty | n/a | n/a（单资源页无 empty） |
| 详情 | 404 | ? | <NotFoundPanel>（M2 视觉收尾 H5 已接入） |
| 详情 | loading | ? | <DetailSkeleton> |
| 详情 | timeline loading | ? | <TimelineSkeleton> |
| 详情 | error | ? | <ErrorState> |
```

把每行的"当前实现"填入（grep 结果），凡是不等于"应改"列的，记入下一步要改的项。

- [ ] **Step 3：把 inline 实现改为公共组件**

仅修「不一致项」，不动已用公共组件的：

- inline empty/error/loading → 用公共组件替换
- spinner / `animate-spin` → 用对应 Skeleton 公共组件 + 按钮文字切换（按 mutation 类型）
- 任何 `backdrop-blur` → 直接删（沿用 `bg-black/50`）

- [ ] **Step 4：`prefers-reduced-motion` 兼容回归**

MASTER `globals.css` 已有媒体查询降级 stagger / tbody-fade / transition-duration。本 task 不引入新动画，**只验证已用公共组件不破此承诺**：

```bash
grep -rn "prefers-reduced-motion" frontend/src/
```

确认 globals.css 媒体查询仍在；新加的代码无 `animation`/`transition` 硬编码（应走 token / Tailwind utility）。

- [ ] **Step 5：本地视觉校对**

- 清空数据库或临时构造空数据：3 页空态视觉一致（全用 EmptyState 组件）
- 断网或 mock 503：3 页 error 一致（全用 ErrorState）
- mock slow query：3 页 loading 一致（全用 Skeleton 公共组件，**无 spinner**）
- 浏览器 DevTools 强制 `prefers-reduced-motion: reduce`：动画降级生效

**停止条件**：3 页同状态全用公共组件；红线 grep 0 命中；reduced-motion 媒体查询生效。

- [ ] **Step 4：commit**

```bash
git add frontend/src/
git commit -m "polish(state): dashboard / 列表 / 详情 三页空错loading态视觉收口

M4-B 修复点 5：3 页对应状态组件视觉一致——同样空态用同样组件，
同 loading 用同 skeleton，同 error 用同 banner（color token / icon）。"
```

---

## Phase 8：smoke + PR

### Task 8.1：本地 smoke

- [ ] **Step 1：跑全后端测 + lint**

```bash
uv run ruff check . && uv run ruff format --check . && uv run pytest
```

期望全绿。

- [ ] **Step 2：跑前端全测 + lint + tsc**

```bash
pnpm --dir frontend lint
pnpm --dir frontend exec tsc -b
pnpm --dir frontend test
```

期望全绿。

- [ ] **Step 3：跑 e2e**

```bash
pnpm --dir frontend e2e
```

期望全绿（含新加的列表排序 spec）。

- [ ] **Step 4：用 Playwright MCP 视觉烟测**

仅本地（非固化 e2e），用 MCP：

- `browser_navigate` → `http://localhost:5173/dashboard`
  - `browser_snapshot` → 校 Y 轴显示 name + 卡片背景协调 + filter toggle 文案 "显示退役"
- `browser_navigate` → `http://localhost:5173/`
  - `browser_snapshot` → 校 type / status 列表头可点击排序
  - `browser_click` 在 status 列表头 → 第一行变 IDLE
- `browser_navigate` → `http://localhost:5173/assets/<id>`
  - 模拟点击附件缩略图，校 lightbox 撑满 90vw + 只有一个 X
- 模拟空数据库
  - 三页空态视觉一致

如某项不通过，回到对应 Phase 修。

### Task 8.2：开 PR

- [ ] **Step 1：push + 开 PR**

```bash
git push -u origin feat/m4-visual-polish
gh pr create --title "feat: M4 视觉打磨主 PR（dialog 抽离 + 配色精打磨 + 看板/列表/lightbox/排序/flaky 修）" --body "$(cat <<'EOF'
## Summary

M4 主 PR 单包 6 子项：

- **M4-A**：抽 useFormDialog hook 收敛 CheckoutDialog / ReturnDialog 样板（各减 ~30 行）
- **M4-B**：配色精打磨 5 修复点
  - 看板背景割裂修（全局 body bg-muted/30）
  - dashboard / 列表 filter toggle 文案统一「显示退役」
  - toggle / chip 样式收敛
  - status 色 token 6 态对比度校准至 WCAG AA（重点 BROKEN）
  - 空 / 错 / loading 态视觉收口（dashboard / 列表 / 详情 3 页）
- **M4-C**：看板可用性（#13）—— IdleTopItem 加 name，Y 轴 dataKey → name，Tooltip 副标显示 asset_code，看板排版微调
- **M4-D**：lightbox（#14）—— !max-w-[90vw] 覆盖 sm:max-w-sm，showCloseButton=false 关默认 X
- **M4-E**：列表排序（#15）—— type / status 两列删 enableSorting: false，status 加 sortingFn 按 ASSET_STATUS_VALUES 下标排序
- **M4-F**：asset-header.test.tsx 时间敏感 flaky 用 vi.useFakeTimers 修

## Test plan

- [x] 后端：stats_service / stats_routes idle_top 含 name 字段 2 case
- [x] 前端 unit：use-form-dialog 2 case / assets-table-sorting 2 case / attachment-lightbox 2 case / asset-header 既有连跑 10 次无 flaky
- [x] e2e：列表排序新 spec PASS
- [x] 视觉烟测（Playwright MCP）：dashboard / 列表 / 详情 / lightbox / 空错loading 三页全通过

## 范围

严格 P 幅度（spec 决策）—— 不动 MASTER.md 整体色板架构，仅修具体问题点。
无 db migration，无 CLI 改动，仅 1 处后端 schema（IdleTopItem 加 name）。

闭环 issue #13 / #14 / #15 + followup-allocation 衍生 minor（filter toggle 文案 / asset-header flaky）。
spec：docs/superpowers/specs/2026-05-17-m4-batch-plan-design.md M4 主 PR 段。
EOF
)"
```

- [ ] **Step 2：等 CI + merge**

```bash
gh pr checks <pr-number>
# 期望 backend + frontend + e2e 全绿
gh pr merge --squash --delete-branch
```

- [ ] **Step 3：发版 v2.2.0**

```bash
# 更新 pyproject.toml version → "2.2.0"
# 更新 frontend/package.json version → "2.2.0"
# 写 docs/superpowers/release-notes-v2.2.0.md
git tag v2.2.0
git push origin v2.2.0
```

---

## Self-Review Checklist

- [x] Spec coverage：
  - M4-A useFormDialog ✓ Phase 5
  - M4-B 5 修复点（背景割裂 / toggle 文案 / chip 样式 / status 色 token / 空错loading）✓ Phase 7
  - M4-C 看板 Y 轴 + 后端 IdleTopItem name + 排版 ✓ Phase 1, 2
  - M4-D lightbox ✓ Phase 4
  - M4-E 列表排序 ✓ Phase 3
  - M4-F asset-header flaky ✓ Phase 6
- [x] 类型一致：useFormDialog 泛型 `<T extends Record<string, unknown>>` 在 hook 定义 + checkout / return 两处调用一致
- [x] 无 placeholder：每 phase 含完整代码 + 测试 + commit msg
- [x] TDD：M4-C / M4-D / M4-E / M4-F 均先测后实现；M4-A hook 也是先测；M4-B 是视觉打磨偏目测，依靠人工 smoke
- [x] 子项间不互依：可任意 phase 顺序做（实际推荐先后端 Phase 1 让 gen:api 早跑）

## 风险

- **M4-B 视觉收尾偏主观**：Phase 7 三 task 每个都有"停止条件"显式列出（plan stop conditions 满足即停）—— scope creep 防御
- **Y 轴 width 90 → 140 可能不够**：长资产名（>10 中文字符）可能溢出。后备方案：tick 加 `tickFormatter` 截断 + tooltip 显示全名
- **CheckoutDialog 现有 e2e（spec 11 reassign-dialog 风格）依赖原 onOpenChange 行为**：useFormDialog 内部 `onOpenChange(false)` 时机与原实现保持一致（mutation 成功后调用）。如 e2e 撞 dialog 关闭时机，回退到 inline `mutation.mutateAsync.then(...).catch(...)` 模式
- **配色对比度校准**：用 DevTools 取值需仔细，最稳是用色板工具直接读 token 计算
- **lightbox `!max-w-` important 与 tailwind-merge**：tailwind-merge 对 `!` 前缀的处理需 v2+，确认 frontend 用的 tailwind-merge 版本支持
- **看板排版微调可能不一定明显**：本 plan 限定改 dashboard-page / dashboard-header 两文件，不深入 chart 内部——足够小，目测能看出变化即停
