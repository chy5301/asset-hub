# PR-2：看板修复 + 列表 page-header 统一 + toggle 统一 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 收口视觉一致性 batch 的剩余项：看板背景去渐变（D1）、看板右列布局修复（D2）、三页 page-header 规范统一（§W-列表）、列表/看板 toggle 统一为语义图标共享组件（§S），可选修逾期角标加载闪动（E）。

**Architecture:** 纯前端视觉/结构调整，无 schema/后端改动。D1/D2 改 `dashboard-page.tsx`；§S 抽 `StatusFilterToggle` 共享组件（基于 shadcn `Toggle` + 语义 Lucide 图标 + status token），`assets-filters.tsx` 与 `dashboard-header.tsx` 都用它；§W-列表统一 `/` 与 `/types` 列表页头（标题对齐 nav 标签 + 计数副标题），看板保持 hero。决策依据见 `docs/superpowers/specs/2026-05-26-ui-consistency-batch-design.md` §视觉决策 决策 1/4/5/6 + E。

**Tech Stack:** React 19 + TanStack Router/Query + vitest + Testing Library。**视觉验证一律先在浅色模式跑**（作者主用浅色；见 playwright 烟测 task）。

---

## File Structure

- **Modify** `frontend/src/features/dashboard/dashboard-page.tsx` — D1（去 radial 背景）+ D2（右列 flex 布局）
- **Create** `frontend/src/components/status/status-filter-toggle.tsx` — §S 共享状态过滤 toggle（语义图标 + status token）
- **Create** `frontend/tests/components/status-filter-toggle.test.tsx` — §S 组件单测
- **Modify** `frontend/src/features/assets/list/assets-filters.tsx` — §S 两个 toggle 改用共享组件
- **Modify** `frontend/src/features/dashboard/dashboard-header.tsx` — §S 用共享组件替换 TogglePill（圆点→图标）
- **Modify** `frontend/tests/components/dashboard-header.test.tsx` — 适配 §S 重构
- **Modify** `frontend/src/features/types/list/types-page.tsx` — §W 标题「类型管理」→「类型」
- **Modify** `frontend/src/routes/index.tsx` — §W 资产列表补 page-header（标题「资产」+ 计数 + 登记按钮上移）
- **Modify** `frontend/src/features/assets/detail/asset-header.tsx` —（可选 E）逾期角标加载态

无后端改动 → **不跑 `gen:api`**。

---

## Task 1: D1 · 看板背景去渐变，用平背景

**Files:** Modify `frontend/src/features/dashboard/dashboard-page.tsx:35-37`

**根因**：`<main>` 套了 `bg-[radial-gradient(...)]`（中心 `oklch(0.985)` 中性灰 → 边缘纯白），而全站其它页面是平 `bg-background`（带蓝调 off-white）→ 浅色模式下看板成了带色差的非均匀面。决策 4：去渐变，用平 `bg-background`。

- [ ] **Step 1: 改背景类**

在 `dashboard-page.tsx` 找到 `<main>` 开标签（约 35-37 行）：
```tsx
    <main
      className="relative min-h-[calc(100vh-4rem)] px-6 py-8 bg-[radial-gradient(50%_60%_at_50%_20%,var(--dashboard-bg-radial-from),var(--dashboard-bg-radial-to))]"
    >
```
改为（去掉 radial，用平背景；保留 `relative min-h px py`）：
```tsx
    <main className="relative min-h-[calc(100vh-4rem)] px-6 py-8 bg-background">
```

- [ ] **Step 2: 验证类型 + 测试不回归**

Run: `pnpm --dir frontend exec tsc -b` → clean。
Run: `pnpm --dir frontend exec vitest run tests/components/dashboard-motion.test.tsx tests/components/dashboard-header.test.tsx` → pass（这些测试不依赖背景类）。
红线 grep（去渐变后应更干净）：`grep -rnE "bg-gradient-to|radial-gradient" frontend/src/features/dashboard/dashboard-page.tsx` → **0 命中**。

- [ ] **Step 3: 提交**

```bash
git add frontend/src/features/dashboard/dashboard-page.tsx
git commit -m "fix(frontend): 看板背景去 radial 渐变改平背景，消除浅色模式色差（D1）"
```

> 注：`globals.css` 的 `--dashboard-bg-radial-from/to` token 暂留（无引用即 dead，删除可放后续清理；本 PR 不强删以缩小改动面）。MASTER.md §Dashboard Atmosphere 的 override 在本 PR 收尾记入 MASTER「实施期纠偏」。

---

## Task 2: D2 · 看板右列布局修复（去强制等高）

**Files:** Modify `frontend/src/features/dashboard/dashboard-page.tsx`（grid 容器 + 右列，约 51、61 行）

**根因**：右列 `grid grid-rows-3 ... min-h-[640px]` 把右列强制切 3 等高行（各 ~213px），但每行内的卡片（`<section>`，无 `h-full`）按内容高度浮在行顶 → 下方死空间 = 大间距。决策 5：右列改 `flex flex-col gap-6` 卡片按内容自然堆叠（`HolderLeaderboard` 已自带 `HolderEmpty` 空态，无需新增）。

- [ ] **Step 1: 改 grid 容器 + 右列**

在 `dashboard-page.tsx` 找到外层 grid（约 51 行）：
```tsx
        <div className="grid grid-cols-12 gap-6 min-h-[640px]">
```
改为（去掉 `min-h-[640px]` 强制高度）：
```tsx
        <div className="grid grid-cols-12 gap-6 items-start">
```
（`items-start` 让左右两列各自顶对齐、按内容高度，不再相互拉伸。）

找到右列容器（约 61 行）：
```tsx
          <div className="col-span-6 grid grid-rows-3 gap-6">
```
改为（自然堆叠，不等高）：
```tsx
          <div className="col-span-6 flex flex-col gap-6">
```
左列 `<motion.div ... className="col-span-6">` 不变。三个右列 `motion.div`（type/status/holder）不变。

- [ ] **Step 2: 验证**

Run: `pnpm --dir frontend exec tsc -b` → clean。
Run: `pnpm --dir frontend exec vitest run tests/components/dashboard-motion.test.tsx` → pass（motion 三时刻测试不依赖等高布局；若该测试断言了 `grid-rows-3` 或 `min-h`，更新断言为新结构——先读测试确认）。

- [ ] **Step 3: 提交**

```bash
git add frontend/src/features/dashboard/dashboard-page.tsx
git commit -m "fix(frontend): 看板右列改自然堆叠，消除强制等高的死空间间距（D2）"
```

---

## Task 3: §S · 抽共享 StatusFilterToggle（语义图标）

**Files:**
- Create: `frontend/src/components/status/status-filter-toggle.tsx`
- Test: `frontend/tests/components/status-filter-toggle.test.tsx`

决策 6：列表与看板的「显示退役/显示注销」toggle 是两套实现（assets 用 shadcn Toggle + 语义图标 Moon/Archive；dashboard 用自定义 TogglePill + 圆点）。统一为一个共享组件，**指示符用语义 Lucide 图标**（Moon=退役 / Archive=注销，与 timeline RETIRE=Moon 一致），基于 shadcn `Toggle`。

- [ ] **Step 1: 写失败测试**

```tsx
// frontend/tests/components/status-filter-toggle.test.tsx
import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Moon } from "lucide-react";

import { StatusFilterToggle } from "@/components/status/status-filter-toggle";

describe("StatusFilterToggle", () => {
  it("渲染 label + 图标，aria-label 正确", () => {
    render(
      <StatusFilterToggle
        pressed={false}
        onPressedChange={vi.fn()}
        icon={Moon}
        label="显示退役"
        status="retired"
      />,
    );
    expect(screen.getByRole("button", { name: "显示退役" })).toBeInTheDocument();
  });

  it("pressed 时 data-state=on，点击回调切换", async () => {
    const onChange = vi.fn();
    render(
      <StatusFilterToggle
        pressed={true}
        onPressedChange={onChange}
        icon={Moon}
        label="显示退役"
        status="retired"
      />,
    );
    const btn = screen.getByRole("button", { name: "显示退役" });
    expect(btn).toHaveAttribute("data-state", "on");
    await userEvent.click(btn);
    expect(onChange).toHaveBeenCalledWith(false);
  });
});
```

- [ ] **Step 2: 跑测试确认失败**

Run: `pnpm --dir frontend exec vitest run tests/components/status-filter-toggle.test.tsx` → FAIL（模块不存在）。

- [ ] **Step 3: 实现**

```tsx
// frontend/src/components/status/status-filter-toggle.tsx
import type { LucideIcon } from "lucide-react";

import { Toggle } from "@/components/ui/toggle";
import { cn } from "@/lib/utils";

type StatusKey = "retired" | "disposed";

const STATUS_TOKEN: Record<StatusKey, string> = {
  retired:
    "data-[state=on]:bg-status-retired/15 data-[state=on]:text-status-retired-fg data-[state=on]:border-status-retired/60",
  disposed:
    "data-[state=on]:bg-status-disposed/15 data-[state=on]:text-status-disposed-fg data-[state=on]:border-status-disposed/60",
};

interface StatusFilterToggleProps {
  pressed: boolean;
  onPressedChange: (pressed: boolean) => void;
  icon: LucideIcon;
  label: string;
  status: StatusKey;
}

/** 列表 / 看板共享的状态过滤 toggle：pill + 语义图标 + status token 染色。 */
export function StatusFilterToggle({
  pressed,
  onPressedChange,
  icon: Icon,
  label,
  status,
}: StatusFilterToggleProps) {
  return (
    <Toggle
      size="sm"
      pressed={pressed}
      onPressedChange={onPressedChange}
      className={cn(
        "rounded-full h-7 px-3 text-xs gap-1.5 transition-colors duration-200 border border-border/40",
        STATUS_TOKEN[status],
      )}
      aria-label={label}
    >
      <Icon className="size-3.5" aria-hidden />
      {label}
    </Toggle>
  );
}
```

- [ ] **Step 4: 跑测试确认通过**

Run: `pnpm --dir frontend exec vitest run tests/components/status-filter-toggle.test.tsx` → PASS（2）。
（若 `@testing-library/user-event` 未安装，改用 `fireEvent.click`——先确认 `frontend/package.json` 是否含 user-event；项目现有测试用什么点击就用什么。）

- [ ] **Step 5: 提交**

```bash
git add frontend/src/components/status/status-filter-toggle.tsx frontend/tests/components/status-filter-toggle.test.tsx
git commit -m "feat(frontend): 抽共享 StatusFilterToggle（语义图标 + status token）"
```

---

## Task 4: §S · 列表与看板改用 StatusFilterToggle

**Files:**
- Modify: `frontend/src/features/assets/list/assets-filters.tsx`
- Modify: `frontend/src/features/dashboard/dashboard-header.tsx`
- Modify: `frontend/tests/components/dashboard-header.test.tsx`

- [ ] **Step 1: assets-filters.tsx 改用共享组件**

当前两个 `<Toggle size="sm" ...>` 块（显示退役 Moon / 显示注销 Archive）替换为共享组件。把 import 里的 `Toggle` 去掉（若不再用），保留 `Moon, Archive`，加 `import { StatusFilterToggle } from "@/components/status/status-filter-toggle";`。两个 toggle 块替换为：
```tsx
      <StatusFilterToggle
        pressed={!!search.show_retired}
        onPressedChange={onToggleRetired}
        icon={Moon}
        label="显示退役"
        status="retired"
      />
      <StatusFilterToggle
        pressed={!!search.show_disposed}
        onPressedChange={onToggleDisposed}
        icon={Archive}
        label="显示注销"
        status="disposed"
      />
```
`onToggleRetired` / `onToggleDisposed` 现有处理函数不变。

- [ ] **Step 2: dashboard-header.tsx 改用共享组件（圆点→图标）**

删除文件内自定义的 `TogglePill` 函数 + 其 `TogglePillProps`。import 加 `import { Moon, Archive } from "lucide-react";` 和 `import { StatusFilterToggle } from "@/components/status/status-filter-toggle";`（保留 `HelpCircle`）。把右侧两个 `<TogglePill .../>` 替换为：
```tsx
        <StatusFilterToggle
          pressed={includeRetired}
          onPressedChange={(next) =>
            onToggle({ include_retired: next, include_disposed: includeDisposed })
          }
          icon={Moon}
          label="显示退役"
          status="retired"
        />
        <StatusFilterToggle
          pressed={includeDisposed}
          onPressedChange={(next) =>
            onToggle({ include_retired: includeRetired, include_disposed: next })
          }
          icon={Archive}
          label="显示注销"
          status="disposed"
        />
```
其余（h1「看板」+ 副标 + HelpCircle）不变。

- [ ] **Step 3: 适配 dashboard-header.test.tsx**

先读该测试。它原来断言 TogglePill 的 dot/文案/点击。改为断言 `StatusFilterToggle` 渲染的 button（`getByRole("button", { name: "显示退役" })` / `"显示注销"`）+ 点击触发 `onToggle`。保留"点击切换 include_retired/include_disposed"的行为断言（核心），仅调整选择器（dot span → button aria-label）。不要删覆盖。

- [ ] **Step 4: 验证**

Run: `pnpm --dir frontend exec vitest run tests/components/dashboard-header.test.tsx tests/hooks/assets-filters-toggle.test.tsx tests/components/status-filter-toggle.test.tsx` → all pass。（`assets-filters-toggle.test.tsx` 若断言了旧 Toggle 的 className，更新到共享组件渲染的等价断言。）
Run: `pnpm --dir frontend exec tsc -b` → clean。
Run: `pnpm --dir frontend lint` → 0 errors。

- [ ] **Step 5: 提交**

```bash
git add frontend/src/features/assets/list/assets-filters.tsx frontend/src/features/dashboard/dashboard-header.tsx frontend/tests/components/dashboard-header.test.tsx frontend/tests/hooks/assets-filters-toggle.test.tsx
git commit -m "refactor(frontend): 列表与看板 toggle 统一用 StatusFilterToggle（§S）"
```

---

## Task 5: §W-列表 · page-header 规范统一

**Files:**
- Modify: `frontend/src/features/types/list/types-page.tsx`
- Modify: `frontend/src/routes/index.tsx`

决策 1：统一「列表页头」=`<h1 text-xl font-semibold>` + 计数副标题 `<p text-sm text-muted-foreground>`，右侧主操作。标题对齐 nav 标签：`资产` / `类型`（从「类型管理」改）/ `看板`（已是）。`/` 资产列表当前**无标题**——补上；filters 移到标题行下方。

- [ ] **Step 1: types-page.tsx 标题改名**

找到 `<h1 className="text-xl font-semibold">类型管理</h1>`，改为：
```tsx
          <h1 className="text-xl font-semibold">类型</h1>
```
副标题 `共 N 个类型` 保留不变。（已是 `text-xl` + 计数副标题 + 右侧新建按钮，符合规范，仅改标题文案。）

- [ ] **Step 2: index.tsx 资产列表补 page-header**

当前 `AssetListPage` 的 return 顶部是：
```tsx
      <section className="space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <AssetsFilters search={search} />
          <div className="flex items-center gap-2">
            <ColumnVisibilityMenu visible={visible} onToggle={toggle} />
            <ExportButton search={search} />
            <Link to="/assets/new"><Button><Plus className="mr-2 h-4 w-4" />登记资产</Button></Link>
          </div>
        </div>
        {renderBody()}
      </section>
```
改为：把「登记资产」按钮上移到新的标题行（与 types 一致：标题左 / 主操作右），filters + 列控制/导出 留在下方一行：
```tsx
      <section className="space-y-4">
        <div className="flex items-end justify-between gap-3">
          <div>
            <h1 className="text-xl font-semibold">资产</h1>
            {query.data && (
              <p className="text-sm text-muted-foreground">共 {query.data.length} 件</p>
            )}
          </div>
          <Link to="/assets/new">
            <Button>
              <Plus className="mr-2 h-4 w-4" />
              登记资产
            </Button>
          </Link>
        </div>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <AssetsFilters search={search} />
          <div className="flex items-center gap-2">
            <ColumnVisibilityMenu visible={visible} onToggle={toggle} />
            <ExportButton search={search} />
          </div>
        </div>
        {renderBody()}
      </section>
```
（`query` 已在组件作用域；`query.data` 为筛选后列表，`.length` = 当前匹配件数。`items-end` 与 types-page 标题行一致。）

- [ ] **Step 3: 验证**

Run: `pnpm --dir frontend exec tsc -b` → clean。
Run: `pnpm --dir frontend test` → all pass。若有列表页测试断言了顶栏结构（如 `tests/unit/assets-table*.test.tsx` 或 list 相关），确认未被破坏；本改动不动表格/筛选逻辑，只重排页头。
Run: `pnpm --dir frontend lint` → 0 errors。

- [ ] **Step 4: 提交**

```bash
git add frontend/src/features/types/list/types-page.tsx frontend/src/routes/index.tsx
git commit -m "feat(frontend): 列表 page-header 统一（标题对齐 nav：资产/类型；资产列表补标题+计数）（§W-列表）"
```

---

## Task 6（可选 E）: 逾期角标加载闪动

**Files:** Modify `frontend/src/features/assets/detail/asset-header.tsx`

`useOverdueForOpenCheckout` 在 transitions 加载期返回 null → `AssetTitleAccessory` 角标"先无后突现"。可接受性低、修复廉价。**可选**：transitions 未加载完时不渲染（现状）已是无闪动的最稳妥形态，真正的"闪动"来自加载完成的瞬时插入。

- [ ] **Step 1: 评估是否值得做**

读 `useTransitionsQuery` 是否暴露 `isLoading`。若要消闪动：`AssetTitleAccessory` 在 `transitions === undefined`（加载中）时返回一个等宽占位（`<span className="inline-block h-5 w-16" aria-hidden />`）避免布局跳动；加载完再渲染真角标。**若占位反而引入视觉噪音，则维持现状并在 PR 描述里标注 E 不做**（决策文档已列 E 为可选）。

- [ ] **Step 2:（若做）实现 + 验证 + 提交**

按上述加占位；`pnpm --dir frontend exec vitest run tests/components/asset-header.test.tsx` 确认现有角标测试仍 pass（占位不影响 `findByText` 角标断言）。提交 `fix(frontend): 逾期角标加载占位消除布局跳动（E）`。

> 默认建议：**E 不做**（ROI 低，现状无硬伤），把精力收在 D1/D2/§S/§W。最终由实施者按 Step 1 评估决定。

---

## Task 7: 全量验证 + 浅色模式 playwright 烟测 + PR

- [ ] **Step 1: 全量 gate**

Run: `pnpm --dir frontend test` → all pass。
Run: `pnpm --dir frontend exec tsc -b` → clean。
Run: `pnpm --dir frontend lint` → 0 errors。
红线 grep（D1 去渐变后应更干净）：`grep -rnE "scale-|animate-spin|backdrop-blur|bg-gradient-to|radial-gradient" frontend/src` → 仅历史 `animate-pulse`（skeleton），无新增、无 radial-gradient。

- [ ] **Step 2: 浅色模式 playwright MCP 烟测（强制先浅色）**

启动 `uv run asset-hub serve start --mode dev`。**先在浅色模式**（顶栏「切换主题」→ 浅色，或确认 localStorage theme=light）走查：
1. `/dashboard`：背景**平整无色差**（D1）；右列三卡（类型分布/状态分布/保管人持有）**自然堆叠、无大间距死空间**（D2）；toggle 是**图标 pill**（Moon/Archive）且按下态清晰（§S）。
2. `/`：顶部有**标题「资产」+ 共 N 件**，下方 filters 行；filter 的「显示退役/显示注销」是**图标 pill**（§S）。
3. `/types`：标题为**「类型」**（非「类型管理」）+ 共 N 个。
4. 三页 page-header 风格一致（标题左 / 操作右）。
截图留档（浅色）。**若要覆盖暗色，再切暗色复测一遍**（作者要求：测暗色则两种都测）。

- [ ] **Step 3: 收尾 MASTER 实施期纠偏 + 推 PR**

在 `design-system/asset-hub/MASTER.md`「实施期纠偏」追加一段（PR-2）：记录 D1 去 Dashboard Atmosphere（radial gradient）override、§S toggle 统一、§W page-header 规范、Pre-Delivery Checklist 7 项 + 红线结果。提交后推分支建 PR：

```bash
git add design-system/asset-hub/MASTER.md
git commit -m "docs(design): MASTER 记录 PR-2 实施期纠偏（D1 去 atmosphere / §S toggle / §W page-header）"
git push -u origin HEAD
gh pr create --base main --title "feat(frontend): 看板修复 + 列表 page-header 统一 + toggle 统一（§W-列表/D1/D2/§S）" --body "<summary + 浅色烟测 test plan>"
```

---

## Self-Review

**Spec 覆盖（决策 1/4/5/6 + E）：** D1 去渐变=Task 1（决策 4）；D2 右列布局=Task 2（决策 5）；§S 共享 toggle=Task 3+4（决策 6，语义图标）；§W page-header 统一=Task 5（决策 1，标题对齐 nav + 资产补标题）；E 可选=Task 6。✅ 覆盖完整。

**占位符扫描：** D1/D2/§S/§W 均给完整替换代码；E 明确标"默认不做+评估条件"，非占位。Task 7 PR body 留 `<summary>` 占位是 gh 命令模板，实施时填实际内容。✅

**类型一致性：** `StatusFilterToggle` props（`pressed/onPressedChange/icon/label/status`）在 Task 3 定义，Task 4 在 assets-filters + dashboard-header 一致调用；`status` 仅 `"retired"|"disposed"` 两值，两处调用都在范围内。✅

**注意点：** 纯前端无 schema 改动；视觉验证**先浅色**（作者主用浅色，本批问题如 D1 色差只在浅色明显）；`HolderLeaderboard` 已自带 `HolderEmpty`，D2 无需新增空态；`globals.css` 的 dashboard radial token 留作 dead（不强删）。
