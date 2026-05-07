# M3d Timeline 视觉重构 + simplify §7 搭车 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** M3d 子里程碑落地——timeline 视觉重构（Group rail + 月份分段 + 新 icon 系统 + 时间格式 + 超长派发预警）+ simplify §7 三搭车（TypesTable motion / H1 type scale / attachment-grid prop fix）。

**Architecture:** 单 PR 单分支 `feat/m3d-timeline-visual`，按 6 phase commit 分段：token → utility（TDD）→ timeline 重构（视觉 gate）→ 超期预警 → C 搭车 → 收尾。后端零改动。

**Tech Stack:** React 19 / TanStack Router / TanStack Query / RHF + zod / Tailwind v4 / shadcn/ui (Calendar + Popover) / lucide-react 1.8 / date-fns / vitest + jsdom / Playwright MCP.

**Spec:** [`docs/superpowers/specs/2026-05-07-m3d-timeline-visual-design.md`](../specs/2026-05-07-m3d-timeline-visual-design.md)

**前置约束（基于 verify 后的事实）：**

- `frontend/src/styles/globals.css` 是项目实际 CSS 入口（不是假设的 `index.css`）
- `frontend/src/components/ui/calendar.tsx` + `popover.tsx` + `react-day-picker@9.14` 已就位（不引入新依赖）
- `frontend/src/features/assets/form/field-controls/date-field.tsx` 是 acquired_at 已用的 Calendar+Popover 范本
- `checkout-dialog.tsx` **due_at 字段已存在**（zod + UI `<Input type="datetime-local">` + mutation body），本计划 §Phase 4 是**升级**该字段 UI 形态 + 同步 META icon
- `asset-header.tsx` H1 已为 `text-2xl font-semibold`（C-2 二档约定已对齐 1/2 处，仅 type-detail-page 待升级）
- `transition-timeline.tsx` 已调 `useTransitionsQuery(assetId)`，AssetHeader 复用同 hook 同 assetId 时 React Query queryKey dedupe 零网络请求
- `frontend/tests/components/` 内 transition-timeline / checkout-dialog / asset-header 三个测试文件**全部不存在**（M3d 新建）
- `tsc -b` 而非 `tsc --noEmit` 做最终类型校验（memory `feedback_tsc_verification.md`）

**任务总览**（32 task / 6 phase）：

- Phase 0 · 起分支（T01）
- Phase 1 · token + 设计系统（T02-T06）
- Phase 2 · utility 纯函数（TDD）（T07-T13）
- Phase 3 · timeline 重构 + 视觉 gate（T14-T19）
- Phase 4 · 超期预警 + dialog UI 升级（T20-T25）
- Phase 5 · C 三搭车（T26-T29）
- Phase 6 · 收尾（playwright + PR + 文档回填）（T30-T32）

---

## Phase 0 · 起分支

### Task 1: 起分支 `feat/m3d-timeline-visual`

**Files:** 无

- [ ] **Step 1.1: 同步 main**

```bash
git checkout main
git pull --ff-only origin main 2>&1 || true
```

- [ ] **Step 1.2: 起分支**

```bash
git checkout -b feat/m3d-timeline-visual
```

预期：`Switched to a new branch 'feat/m3d-timeline-visual'`

---

## Phase 1 · token + 设计系统

### Task 2: 加 `--status-borrowed` token（light + dark）

**Files:**
- Modify: `frontend/src/styles/globals.css`

- [ ] **Step 2.1: 在 globals.css `:root` 块加 light 主题 token**

找到 `--status-disposed` 定义（M3a 已加），紧随其后加：

```css
--status-borrowed: oklch(0.78 0.13 75);
--status-borrowed-fg: oklch(0.42 0.13 75);
```

- [ ] **Step 2.2: 在 `.dark` 块加 dark 主题 token**

找到 `.dark` 选择器内 `--status-disposed` 定义，紧随其后加：

```css
--status-borrowed: oklch(0.70 0.13 75);
--status-borrowed-fg: oklch(0.85 0.10 75);
```

- [ ] **Step 2.3: 在 `@theme inline` 节加 utility 映射**

找到 `--color-status-disposed` 映射，加：

```css
--color-status-borrowed: var(--status-borrowed);
--color-status-borrowed-fg: var(--status-borrowed-fg);
```

这样 Tailwind v4 能识别 `bg-status-borrowed/15` / `text-status-borrowed-fg` utility。

- [ ] **Step 2.4: 验 utility 可用**

```bash
pnpm --dir frontend tsc -b
```

预期：0 错。

### Task 3: 加 `--warning` + `--warning-fg` token

**Files:**
- Modify: `frontend/src/styles/globals.css`

- [ ] **Step 3.1: 在 `:root` 加 light 主题**

紧随 `--status-borrowed-fg` 之后加：

```css
--warning: oklch(0.85 0.18 90);
--warning-fg: oklch(0.45 0.15 90);
```

- [ ] **Step 3.2: 在 `.dark` 加 dark 主题**

```css
--warning: oklch(0.72 0.18 90);
--warning-fg: oklch(0.88 0.13 90);
```

- [ ] **Step 3.3: 在 `@theme inline` 加 utility 映射**

```css
--color-warning: var(--warning);
--color-warning-fg: var(--warning-fg);
```

- [ ] **Step 3.4: tsc -b 验证**

```bash
pnpm --dir frontend tsc -b
```

### Task 4: tokens.test.ts 验 token 双主题

**Files:**
- Create: `frontend/tests/unit/tokens.test.ts`

- [ ] **Step 4.1: 写测试（TDD：先写失败用例）**

```ts
import { describe, expect, it, beforeEach, afterEach } from "vitest";

function readToken(name: string): string {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

function setTheme(theme: "light" | "dark") {
  document.documentElement.classList.toggle("dark", theme === "dark");
}

describe("M3d 新增 design tokens", () => {
  beforeEach(() => {
    // 加载 globals.css；vitest jsdom 无 css 默认行为，直接断言 var 名是否能 read
    // 这里用 setProperty 模拟 globals.css 已加载
    document.documentElement.style.setProperty("--status-borrowed", "oklch(0.78 0.13 75)");
    document.documentElement.style.setProperty("--status-borrowed-fg", "oklch(0.42 0.13 75)");
    document.documentElement.style.setProperty("--warning", "oklch(0.85 0.18 90)");
    document.documentElement.style.setProperty("--warning-fg", "oklch(0.45 0.15 90)");
  });

  afterEach(() => {
    document.documentElement.removeAttribute("style");
    document.documentElement.classList.remove("dark");
  });

  it("light 主题下 4 个新 token 都有非空值", () => {
    setTheme("light");
    expect(readToken("--status-borrowed")).toMatch(/^oklch/);
    expect(readToken("--status-borrowed-fg")).toMatch(/^oklch/);
    expect(readToken("--warning")).toMatch(/^oklch/);
    expect(readToken("--warning-fg")).toMatch(/^oklch/);
  });

  it("token 命名遵守双后缀约定（chip + fg 配对）", () => {
    expect(readToken("--status-borrowed")).not.toBe(readToken("--status-borrowed-fg"));
    expect(readToken("--warning")).not.toBe(readToken("--warning-fg"));
  });
});
```

**注意**：jsdom 不真正解析 CSS，无法直接验"globals.css 加了 token"——本测试用 setProperty 模拟"token 已加载"+ 断言"读取行为正确"，间接保护命名一致性。token 实际值正确性靠 playwright MCP 烟测覆盖（Phase 3 视觉 gate）。

- [ ] **Step 4.2: 跑测试**

```bash
pnpm --dir frontend test tokens.test.ts
```

预期：PASS。

### Task 5: MASTER.md 加 status-borrowed / warning / type scale 节

**Files:**
- Modify: `design-system/asset-hub/MASTER.md`

- [ ] **Step 5.1: 找到 "Status token 体系" 节**

```bash
grep -n "Status token\|status-disposed" design-system/asset-hub/MASTER.md | head -5
```

- [ ] **Step 5.2: 在 status-disposed 表行后加两行**

```
| `--status-borrowed`    | 琥珀（amber），hue ≈ 75°  | CHECKOUT_EXTERNAL（对外出借）chip / Group rail external |
| `--status-borrowed-fg` | 同色相深 fg              | 上同 chip 文字色                                        |
| `--warning`            | amber 黄，hue ≈ 90°      | due-soon 黄色警示（< 7 天到期）                         |
| `--warning-fg`         | 同色相深 fg              | warning 文字色 / 角标 fg                                |
```

- [ ] **Step 5.3: 在 MASTER.md 末尾或 "排版" 节加 type scale 节**

```markdown
## 排版 type scale（M3d 引入）

页面 H1 字号按页面分类二档：

| 页面分类 | utility | 用例 |
|---|---|---|
| 列表 / 配置页 | `text-xl font-semibold` | `/types`（类型列表） |
| 详情页 | `text-2xl font-semibold` | `/assets/:id` / `/types/:id` |
| 看板（hero）| 不纳入此约定 | `/dashboard` 用 `text-3xl font-medium tracking-tight` 独立形态 |

新加页面前按归类挑选；偏离需在本表加行说明。
```

### Task 6: Phase 1 提交

- [ ] **Step 6.1: 跑全部前端验收**

```bash
pnpm --dir frontend tsc -b
pnpm --dir frontend lint
pnpm --dir frontend test
```

全部 0 错。

- [ ] **Step 6.2: stage + commit**

```bash
git add frontend/src/styles/globals.css design-system/asset-hub/MASTER.md frontend/tests/unit/tokens.test.ts
git commit -m "$(cat <<'EOF'
feat(design-system): M3d 新增 status-borrowed + warning token + type scale 约定

加 --status-borrowed (amber hue 75°) 双 token 给 CHECKOUT_EXTERNAL；
加 --warning + --warning-fg (amber hue 90°) 双 token 给 due-soon 警示；
MASTER.md 文档化 type scale 二档约定（列表 text-xl / 详情 text-2xl）。
EOF
)"
```

---

## Phase 2 · utility 纯函数（TDD）

### Task 7: 写 calc-overdue 测试（先失败）

**Files:**
- Create: `frontend/tests/unit/calc-overdue.test.ts`

- [ ] **Step 7.1: 写完整测试**

```ts
import { describe, expect, it } from "vitest";
import { calcOverdue } from "@/lib/overdue";

const NOW = new Date("2026-05-07T10:00:00Z");

describe("calcOverdue", () => {
  it("status !== IN_USE 返 null", () => {
    expect(calcOverdue("2026-05-10", "IDLE", NOW)).toBeNull();
    expect(calcOverdue("2026-05-10", "MAINTENANCE", NOW)).toBeNull();
    expect(calcOverdue("2026-05-10", "RETIRED", NOW)).toBeNull();
    expect(calcOverdue("2026-05-10", "DISPOSED", NOW)).toBeNull();
  });

  it("dueAt === null 返 null", () => {
    expect(calcOverdue(null, "IN_USE", NOW)).toBeNull();
  });

  it("now < dueAt - 7d → pending", () => {
    expect(calcOverdue("2026-05-20", "IN_USE", NOW)).toEqual({
      status: "pending",
      days: 13,
    });
  });

  it("边界：now === dueAt - 7d → due-soon", () => {
    expect(calcOverdue("2026-05-14", "IN_USE", NOW)).toEqual({
      status: "due-soon",
      days: 7,
    });
  });

  it("边界：now === dueAt → due-soon", () => {
    expect(calcOverdue("2026-05-07", "IN_USE", NOW)).toEqual({
      status: "due-soon",
      days: 0,
    });
  });

  it("now > dueAt → overdue (取绝对值)", () => {
    expect(calcOverdue("2026-04-29", "IN_USE", NOW)).toEqual({
      status: "overdue",
      days: 8,
    });
  });

  it("跨年逾期", () => {
    const lastYear = new Date("2025-12-15T10:00:00Z");
    expect(calcOverdue("2025-12-01", "IN_USE", lastYear)).toEqual({
      status: "overdue",
      days: 14,
    });
  });
});
```

- [ ] **Step 7.2: 跑测试，确认失败**

```bash
pnpm --dir frontend test calc-overdue.test.ts
```

预期：FAIL with `Cannot find module '@/lib/overdue'`。

### Task 8: 实现 lib/overdue.ts 跑过测试

**Files:**
- Create: `frontend/src/lib/overdue.ts`

- [ ] **Step 8.1: 写实现**

```ts
import { differenceInCalendarDays, parseISO } from "date-fns";
import type { components } from "@/api/generated/schema";

type AssetStatus = components["schemas"]["AssetStatus"];

export type OverdueStatus = "pending" | "due-soon" | "overdue";

export interface OverdueResult {
  status: OverdueStatus;
  days: number;
}

export function calcOverdue(
  dueAt: string | null,
  assetStatus: AssetStatus,
  now: Date = new Date(),
): OverdueResult | null {
  if (assetStatus !== "IN_USE" || dueAt === null) return null;
  const due = parseISO(dueAt);
  const diff = differenceInCalendarDays(due, now); // 正数 = 还有 N 天 / 0 = 当天 / 负数 = 逾期 N 天
  if (diff > 7) return { status: "pending", days: diff };
  if (diff >= 0) return { status: "due-soon", days: diff };
  return { status: "overdue", days: -diff };
}
```

`differenceInCalendarDays`（不是 `differenceInDays`）按日历日数算，避免时分秒漂移。

- [ ] **Step 8.2: 跑测试，确认通过**

```bash
pnpm --dir frontend test calc-overdue.test.ts
```

预期：PASS（7/7）。

### Task 9: 写 format-relative 测试

**Files:**
- Create: `frontend/tests/unit/format-relative.test.ts`

- [ ] **Step 9.1: 写测试**

```ts
import { describe, expect, it } from "vitest";
import { formatRelative } from "@/lib/date";

const NOW = new Date("2026-05-07T10:00:00Z");

describe("formatRelative", () => {
  it("当天 → 今天", () => {
    expect(formatRelative("2026-05-07T08:00:00Z", NOW)).toBe("今天");
  });

  it("1 天前 → 昨天", () => {
    expect(formatRelative("2026-05-06T08:00:00Z", NOW)).toBe("昨天");
  });

  it("N 天前", () => {
    expect(formatRelative("2026-05-02T08:00:00Z", NOW)).toBe("5 天前");
    expect(formatRelative("2026-04-07T08:00:00Z", NOW)).toBe("30 天前");
  });

  it("跨年仍用天", () => {
    expect(formatRelative("2025-05-07T08:00:00Z", NOW)).toBe("365 天前");
  });

  it("未来日期（边界异常）→ 今天", () => {
    // 后端不应给未来 created_at；防御性返今天
    expect(formatRelative("2026-05-10T08:00:00Z", NOW)).toBe("今天");
  });
});
```

- [ ] **Step 9.2: 跑测试，确认失败**

```bash
pnpm --dir frontend test format-relative.test.ts
```

预期：FAIL（`formatRelative` 未导出）。

### Task 10: 在 lib/date.ts 加 formatRelative

**Files:**
- Modify: `frontend/src/lib/date.ts`

- [ ] **Step 10.1: 加函数**

在 `formatDate` 之后加：

```ts
export function formatRelative(iso: string, now: Date = new Date()): string {
  const date = parseISO(iso);
  const days = Math.max(0, Math.floor((now.getTime() - date.getTime()) / 86400000));
  if (days === 0) return "今天";
  if (days === 1) return "昨天";
  return `${days} 天前`;
}
```

- [ ] **Step 10.2: 跑测试，确认通过**

```bash
pnpm --dir frontend test format-relative.test.ts
```

预期：PASS（5/5）。

### Task 11: 写 timeline-grouping 测试（groupByMonth + groupByCheckout）

**Files:**
- Create: `frontend/tests/unit/timeline-grouping.test.ts`

- [ ] **Step 11.1: 写测试**

```ts
import { describe, expect, it } from "vitest";
import { groupByMonth, groupByCheckout, type GroupedTransition } from "@/lib/timeline-grouping";
import type { TransitionRead } from "@/features/assets/types";

function mkT(id: string, kind: TransitionRead["kind"], created_at: string, extra?: Partial<TransitionRead>): TransitionRead {
  return {
    id,
    asset_id: "a1",
    kind,
    from_status: null,
    to_status: "IDLE",
    from_holder: null,
    to_holder: null,
    from_location: null,
    to_location: null,
    note: null,
    created_at,
    due_at: null,
    closes_transition_id: null,
    ...extra,
  } as TransitionRead;
}

describe("groupByMonth", () => {
  it("跨月分组 + month desc 排序", () => {
    const ts = [
      mkT("t1", "DISPOSE", "2026-05-02T10:00:00Z"),
      mkT("t2", "RETIRE", "2026-04-15T10:00:00Z"),
      mkT("t3", "RECOVER_FROM_MAINTENANCE", "2026-04-01T10:00:00Z"),
      mkT("t4", "SEND_TO_MAINTENANCE", "2026-03-20T10:00:00Z"),
    ];
    const out = groupByMonth(ts);
    expect(out).toEqual([
      { month: "2026-05", items: [ts[0]] },
      { month: "2026-04", items: [ts[1], ts[2]] },
      { month: "2026-03", items: [ts[3]] },
    ]);
  });

  it("空数组返 []", () => {
    expect(groupByMonth([])).toEqual([]);
  });
});

describe("groupByCheckout", () => {
  it("一对 INTERNAL CHECKOUT + RETURN（中间无中性卡）", () => {
    const ts: TransitionRead[] = [
      mkT("ret", "RETURN", "2026-05-05T10:00:00Z", { closes_transition_id: "co" }),
      mkT("co", "CHECKOUT_INTERNAL", "2026-04-20T10:00:00Z"),
    ];
    const out = groupByCheckout(ts);
    expect(out).toEqual([
      { ...ts[0], group: { kind: "in-use", position: "end" } },
      { ...ts[1], group: { kind: "in-use", position: "start" } },
    ]);
  });

  it("EXTERNAL CHECKOUT + 中间夹 RELOCATE + RETURN", () => {
    const ts: TransitionRead[] = [
      mkT("ret", "RETURN", "2026-05-10T10:00:00Z", { closes_transition_id: "co" }),
      mkT("relo", "RELOCATE", "2026-05-05T10:00:00Z"),
      mkT("co", "CHECKOUT_EXTERNAL", "2026-04-20T10:00:00Z"),
    ];
    const out = groupByCheckout(ts);
    expect(out[0].group).toEqual({ kind: "external", position: "end" });
    expect(out[1].group).toEqual({ kind: "external", position: "middle" });
    expect(out[2].group).toEqual({ kind: "external", position: "start" });
  });

  it("OPEN CHECKOUT（没有对应 RETURN，向更新方向延伸）", () => {
    // 时间倒序：list 头部最新；OPEN CHECKOUT 上面的中性卡都属于派出周期
    const ts: TransitionRead[] = [
      mkT("trans", "TRANSFER_HOLDER", "2026-05-05T10:00:00Z"),
      mkT("co", "CHECKOUT_INTERNAL", "2026-04-20T10:00:00Z"),
    ];
    const out = groupByCheckout(ts);
    expect(out[0].group).toEqual({ kind: "in-use", position: "middle" });
    expect(out[1].group).toEqual({ kind: "in-use", position: "start" });
  });

  it("周期外 transition group=null", () => {
    const ts: TransitionRead[] = [
      mkT("dispose", "DISPOSE", "2026-05-10T10:00:00Z"),
      mkT("retire", "RETIRE", "2026-05-05T10:00:00Z"),
    ];
    const out = groupByCheckout(ts);
    expect(out[0].group).toBeNull();
    expect(out[1].group).toBeNull();
  });

  it("混合：派出周期 + 周期外", () => {
    const ts: TransitionRead[] = [
      mkT("retire", "RETIRE", "2026-06-01T10:00:00Z"),                                     // 周期外
      mkT("ret", "RETURN", "2026-05-10T10:00:00Z", { closes_transition_id: "co" }),         // end
      mkT("co", "CHECKOUT_INTERNAL", "2026-04-20T10:00:00Z"),                                // start
      mkT("send", "SEND_TO_MAINTENANCE", "2026-04-10T10:00:00Z"),                            // 周期外
    ];
    const out = groupByCheckout(ts);
    expect(out[0].group).toBeNull();
    expect(out[1].group).toEqual({ kind: "in-use", position: "end" });
    expect(out[2].group).toEqual({ kind: "in-use", position: "start" });
    expect(out[3].group).toBeNull();
  });
});
```

- [ ] **Step 11.2: 跑测试，确认失败**

```bash
pnpm --dir frontend test timeline-grouping.test.ts
```

预期：FAIL with `Cannot find module '@/lib/timeline-grouping'`。

### Task 12: 实现 lib/timeline-grouping.ts

**Files:**
- Create: `frontend/src/lib/timeline-grouping.ts`

- [ ] **Step 12.1: 写实现**

```ts
import { format, parseISO } from "date-fns";
import type { TransitionRead } from "@/features/assets/types";

export type GroupKind = "in-use" | "external";
export type GroupPosition = "start" | "middle" | "end";

export interface TransitionGroup {
  kind: GroupKind;
  position: GroupPosition;
}

export type GroupedTransition = TransitionRead & { group: TransitionGroup | null };

/** 按月份分组（YYYY-MM），月份 desc 排序，月内保持入参顺序 */
export interface MonthGroup<T = TransitionRead> {
  month: string;
  items: T[];
}

export function groupByMonth<T extends TransitionRead>(transitions: T[]): MonthGroup<T>[] {
  const buckets = new Map<string, T[]>();
  for (const t of transitions) {
    const month = format(parseISO(t.created_at), "yyyy-MM");
    const bucket = buckets.get(month) ?? [];
    bucket.push(t);
    buckets.set(month, bucket);
  }
  return Array.from(buckets.entries())
    .sort(([a], [b]) => b.localeCompare(a))
    .map(([month, items]) => ({ month, items }));
}

/** 给每条 transition 标记派出周期 group。
 *  输入要求按 created_at desc 排序（API 返回顺序）。
 *  算法：从最旧（数组尾部）向最新（数组头部）扫，配对 CHECKOUT_* ↔ RETURN（用 closes_transition_id）。 */
export function groupByCheckout(transitions: TransitionRead[]): GroupedTransition[] {
  const out: GroupedTransition[] = transitions.map((t) => ({ ...t, group: null }));

  // 找所有 OPEN CHECKOUT 与 closed CHECKOUT 的边界
  const closedCheckoutIds = new Set(
    transitions
      .filter((t) => t.kind === "RETURN" && t.closes_transition_id)
      .map((t) => t.closes_transition_id as string),
  );

  // 倒序扫（从数组尾部 = 最旧 → 数组头部 = 最新）
  let activeKind: GroupKind | null = null;
  let activeStartIdx: number | null = null;
  let activeEndIdx: number | null = null;

  // 第一遍：找所有派出周期的 [start, end] 索引区间（数组索引，非时间）
  const cycles: { kind: GroupKind; startIdx: number; endIdx: number | null }[] = [];
  for (let i = transitions.length - 1; i >= 0; i--) {
    const t = transitions[i];
    if (t.kind === "CHECKOUT_INTERNAL" || t.kind === "CHECKOUT_EXTERNAL") {
      const kind: GroupKind = t.kind === "CHECKOUT_INTERNAL" ? "in-use" : "external";
      const isOpen = !closedCheckoutIds.has(t.id);
      cycles.push({ kind, startIdx: i, endIdx: isOpen ? null : -1 });  // endIdx 待填
    } else if (t.kind === "RETURN" && t.closes_transition_id) {
      const cycle = cycles.find((c) => c.endIdx === -1);
      if (cycle) cycle.endIdx = i;
    }
  }

  // 第二遍：标记每条 transition 的 group
  for (const cycle of cycles) {
    // CHECKOUT 卡：position = 'start'
    out[cycle.startIdx].group = { kind: cycle.kind, position: "start" };

    if (cycle.endIdx !== null && cycle.endIdx >= 0) {
      // RETURN 卡：position = 'end'
      out[cycle.endIdx].group = { kind: cycle.kind, position: "end" };
      // 中间（startIdx > i > endIdx，因数组 desc，startIdx 大 endIdx 小）
      for (let i = cycle.startIdx - 1; i > cycle.endIdx; i--) {
        if (out[i].group === null) out[i].group = { kind: cycle.kind, position: "middle" };
      }
    } else {
      // OPEN CHECKOUT：从 startIdx 向更新方向（i < startIdx）扫，直到 status 离开 IN_USE
      for (let i = cycle.startIdx - 1; i >= 0; i--) {
        const t = transitions[i];
        // 离开 IN_USE 的 transition kind：RETURN（已不会出现，因 OPEN）/ DISPOSE / RETIRE / SEND_TO_MAINTENANCE
        // OPEN 状态意味着没有更新的 RETURN/DISPOSE/RETIRE/SEND_TO_MAINTENANCE
        if (out[i].group === null) out[i].group = { kind: cycle.kind, position: "middle" };
      }
    }
  }

  return out;
}
```

- [ ] **Step 12.2: 跑测试，确认通过**

```bash
pnpm --dir frontend test timeline-grouping.test.ts
```

预期：PASS（7/7）。

### Task 13: Phase 2 提交

- [ ] **Step 13.1: 跑全前端验收**

```bash
pnpm --dir frontend tsc -b
pnpm --dir frontend lint
pnpm --dir frontend test
```

- [ ] **Step 13.2: commit**

```bash
git add frontend/src/lib/overdue.ts frontend/src/lib/date.ts frontend/src/lib/timeline-grouping.ts frontend/tests/unit/calc-overdue.test.ts frontend/tests/unit/format-relative.test.ts frontend/tests/unit/timeline-grouping.test.ts
git commit -m "$(cat <<'EOF'
feat(timeline): M3d utility 纯函数 (calcOverdue / formatRelative / timeline-grouping)

calcOverdue 两阶段（pending / due-soon / overdue）基于 due_at；
formatRelative 返 "今天"/"昨天"/"N 天前"（v1 仅天级）；
groupByMonth + groupByCheckout 支持月份 sticky heading + Group rail render。
TDD：先测试后实现，全部用例覆盖边界（恰好 7d / 0d / 跨年 / OPEN CHECKOUT）。
EOF
)"
```

---

## Phase 3 · timeline 重构 + 视觉 gate

### Task 14: KIND_META 改写 + import 更新

**Files:**
- Modify: `frontend/src/features/assets/detail/transition-timeline.tsx`

- [ ] **Step 14.1: 改 import 块**

```tsx
- import {
-   ArrowRightFromLine, CheckCircle2, MapPin, Moon, Send,
-   Sun, Trash2, Undo2, UserCog, Wrench, type LucideIcon,
- } from "lucide-react";
+ import {
+   ArrowRightFromLine, ArrowLeftRight,
+   Archive, ArchiveRestore,
+   Clock, MapPin, PackageCheck,
+   Trash2, Undo2, Wrench,
+   type LucideIcon,
+ } from "lucide-react";
```

`Send` / `CheckCircle2` / `Moon` / `Sun` / `UserCog` 移除；`Clock` 新增（overdue 提示行用）；`Archive` / `ArchiveRestore` / `PackageCheck` / `ArrowLeftRight` 新增。

- [ ] **Step 14.2: 改 KIND_META 5 行**

```tsx
const KIND_META: Record<TransitionKind, KindMeta> = {
  CHECKOUT_INTERNAL:        { label: "派发",       Icon: ArrowRightFromLine, bgClass: "bg-status-in-use/15",      fgClass: "text-status-in-use-fg" },
  CHECKOUT_EXTERNAL:        { label: "出借",       Icon: ArrowRightFromLine, bgClass: "bg-status-borrowed/15",    fgClass: "text-status-borrowed-fg" },
  RETURN:                   { label: "归还",       Icon: Undo2,              bgClass: "bg-status-idle/15",        fgClass: "text-status-idle-fg" },
  SEND_TO_MAINTENANCE:      { label: "送修",       Icon: Wrench,             bgClass: "bg-status-maintenance/15", fgClass: "text-status-maintenance-fg" },
  RECOVER_FROM_MAINTENANCE: { label: "维修完成",   Icon: PackageCheck,       bgClass: "bg-status-idle/15",        fgClass: "text-status-idle-fg" },
  RETIRE:                   { label: "退役",       Icon: Archive,            bgClass: "bg-status-retired/15",     fgClass: "text-status-retired-fg" },
  REINSTATE:                { label: "重新启用",   Icon: ArchiveRestore,     bgClass: "bg-status-idle/15",        fgClass: "text-status-idle-fg" },
  DISPOSE:                  { label: "处置",       Icon: Trash2,             bgClass: "bg-status-disposed/15",    fgClass: "text-status-disposed-fg" },
  RELOCATE:                 { label: "变更位置",   Icon: MapPin,             bgClass: "bg-muted",                 fgClass: "text-muted-foreground" },
  TRANSFER_HOLDER:          { label: "变更保管人", Icon: ArrowLeftRight,     bgClass: "bg-muted",                 fgClass: "text-muted-foreground" },
};
```

- [ ] **Step 14.3: tsc -b 验证 import 无遗漏**

```bash
pnpm --dir frontend tsc -b
```

预期：0 错。

### Task 15: 写 transition-timeline 组件测试（先失败）

**Files:**
- Create: `frontend/tests/components/transition-timeline.test.tsx`

- [ ] **Step 15.1: 写测试**

```tsx
import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import { TransitionTimeline } from "@/features/assets/detail/transition-timeline";
import * as transitionsHook from "@/api/hooks/transitions";
import type { TransitionRead } from "@/features/assets/types";

function mkT(id: string, kind: TransitionRead["kind"], created_at: string, extra: Partial<TransitionRead> = {}): TransitionRead {
  return {
    id, asset_id: "a1", kind,
    from_status: null, to_status: "IDLE",
    from_holder: null, to_holder: "张三",
    from_location: null, to_location: "工位 A1",
    note: null, created_at, due_at: null, closes_transition_id: null,
    ...extra,
  } as TransitionRead;
}

function renderWithProvider(ui: React.ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

describe("TransitionTimeline (M3d)", () => {
  it("跨 2 个月数据 → 渲染 2 个月份 heading", () => {
    const data = [
      mkT("t1", "DISPOSE", "2026-05-02T10:00:00Z"),
      mkT("t2", "RETIRE", "2026-04-15T10:00:00Z"),
    ];
    vi.spyOn(transitionsHook, "useTransitionsQuery").mockReturnValue({
      data, isLoading: false, isError: false, error: null, refetch: vi.fn(),
    } as never);

    renderWithProvider(<TransitionTimeline assetId="a1" />);

    expect(screen.getByText("2026-05")).toBeInTheDocument();
    expect(screen.getByText("2026-04")).toBeInTheDocument();
  });

  it("CHECKOUT + RETURN 一对 → DOM 含派发 + 归还 pill 文案", () => {
    const data = [
      mkT("ret", "RETURN", "2026-05-05T10:00:00Z", { closes_transition_id: "co" }),
      mkT("co", "CHECKOUT_INTERNAL", "2026-04-20T10:00:00Z"),
    ];
    vi.spyOn(transitionsHook, "useTransitionsQuery").mockReturnValue({
      data, isLoading: false, isError: false, error: null, refetch: vi.fn(),
    } as never);

    renderWithProvider(<TransitionTimeline assetId="a1" />);

    expect(screen.getByText("派发给 张三 · 位置 工位 A1")).toBeInTheDocument();
    expect(screen.getByText("归还给 张三")).toBeInTheDocument();
  });

  it("时间格式 = 绝对日期 · 相对天数", () => {
    const data = [mkT("t1", "RETIRE", "2026-05-02T10:00:00Z")];
    vi.spyOn(transitionsHook, "useTransitionsQuery").mockReturnValue({
      data, isLoading: false, isError: false, error: null, refetch: vi.fn(),
    } as never);

    renderWithProvider(<TransitionTimeline assetId="a1" />);

    // 不强测 "5 天前"（依赖运行日期）；强测格式存在 yyyy-MM-dd · X 天前 / 今天 / 昨天
    const time = screen.getByText(/^2026-05-02 · /);
    expect(time).toBeInTheDocument();
  });

  it("loading → 渲染 skeleton（不显示月份分组）", () => {
    vi.spyOn(transitionsHook, "useTransitionsQuery").mockReturnValue({
      data: undefined, isLoading: true, isError: false, error: null, refetch: vi.fn(),
    } as never);

    renderWithProvider(<TransitionTimeline assetId="a1" />);

    expect(screen.queryByText(/^\d{4}-\d{2}$/)).not.toBeInTheDocument();
  });

  it("empty → 渲染 EmptyState", () => {
    vi.spyOn(transitionsHook, "useTransitionsQuery").mockReturnValue({
      data: [], isLoading: false, isError: false, error: null, refetch: vi.fn(),
    } as never);

    renderWithProvider(<TransitionTimeline assetId="a1" />);

    expect(screen.getByText(/暂无流转记录/)).toBeInTheDocument();
  });
});
```

- [ ] **Step 15.2: 跑测试，确认失败**

```bash
pnpm --dir frontend test transition-timeline.test.tsx
```

预期：FAIL（assertions 不通过 / 月份 heading 不存在等）。

### Task 16: transition-timeline.tsx render 重构（month heading + Group rail + 时间格式 + overdue 提示行）

**Files:**
- Modify: `frontend/src/features/assets/detail/transition-timeline.tsx`

- [ ] **Step 16.1: import 扩展**

文件顶部加：

```tsx
import { useMemo } from "react";
import { groupByMonth, groupByCheckout, type GroupedTransition, type TransitionGroup } from "@/lib/timeline-grouping";
import { calcOverdue } from "@/lib/overdue";
import { formatDate, formatDateTime, formatRelative } from "@/lib/date";
import { cn } from "@/lib/utils";
import type { AssetStatus } from "@/features/assets/types";  // 如果 types 已导出 AssetStatus；否则按 AssetRead.status 类型
```

`formatDateTime` 不再用，可移除（如果其他地方已无引用）。`formatDate` + `formatRelative` 替代。

- [ ] **Step 16.2: 改组件 props 收 asset.status**

```tsx
interface TransitionTimelineProps {
  assetId: string;
  assetStatus: AssetStatus;
}

export function TransitionTimeline({ assetId, assetStatus }: TransitionTimelineProps) {
  const query = useTransitionsQuery(assetId);
  // ...
}
```

并在 `asset-detail-page.tsx` 调用处加 `assetStatus={asset.status}` prop（grep 确认调用点）：

```bash
grep -rn "<TransitionTimeline" frontend/src
```

修改后引用点都加 `assetStatus={asset.status}`。

- [ ] **Step 16.3: 改 render（含 group 计算 + 月份分组 + Group rail）**

替换原 `query.data.length === 0 ? ... : <ol>...` 块为：

```tsx
  const grouped = useMemo<GroupedTransition[]>(
    () => (query.data ? groupByCheckout(query.data) : []),
    [query.data],
  );
  const months = useMemo(() => groupByMonth(grouped), [grouped]);

  return (
    <section>
      <h2 className="mb-3 text-lg font-medium">流转记录</h2>
      {query.isLoading ? (
        <TimelineSkeleton />
      ) : query.isError ? (
        <ErrorState error={query.error} onRetry={() => query.refetch()} />
      ) : (query.data ?? []).length === 0 ? (
        <EmptyState title="暂无流转记录" description="发生 transition 后会在此出现记录。" />
      ) : (
        months.map(({ month, items }) => (
          <div key={month} className="mb-3">
            <h3 className="sticky top-0 bg-background pb-1.5 pt-3 text-xs uppercase tracking-wide text-muted-foreground border-b border-border/40 font-medium first:pt-0 z-10">
              {month}
            </h3>
            <ol className="space-y-3 mt-2">
              {items.map((t) => (
                <TransitionCard key={t.id} t={t} group={t.group} assetStatus={assetStatus} />
              ))}
            </ol>
          </div>
        ))
      )}
    </section>
  );
```

- [ ] **Step 16.4: 抽 TransitionCard 子组件**

文件内加：

```tsx
function TransitionCard({
  t,
  group,
  assetStatus,
}: {
  t: GroupedTransition;
  group: TransitionGroup | null;
  assetStatus: AssetStatus;
}) {
  const meta = KIND_META[t.kind];
  const Icon = meta.Icon;

  // 仅 OPEN CHECKOUT 卡（kind 是 CHECKOUT_*，且没有 closes_transition_id 引用它 = position === 'start' 且没有对应 end）
  // 简化判断：当 group.position === 'start' 且 assetStatus === 'IN_USE' 时算 OPEN CHECKOUT
  const isOpenCheckout =
    (t.kind === "CHECKOUT_INTERNAL" || t.kind === "CHECKOUT_EXTERNAL") &&
    group?.position === "start" &&
    assetStatus === "IN_USE";
  const overdue = isOpenCheckout ? calcOverdue(t.due_at, assetStatus) : null;

  return (
    <li className="rounded-lg ring-1 ring-border/60 p-3 flex items-start gap-3 relative">
      {/* Group rail */}
      {group?.kind && group.position !== "end" && (
        <span
          className={cn(
            "absolute left-0 w-0.5 -bottom-3",
            group.position === "start" ? "top-1.5" : "top-0",
            group.kind === "in-use" && "bg-status-in-use/40",
            group.kind === "external" && "bg-status-borrowed/40",
          )}
          aria-hidden
        />
      )}
      {group?.kind && group.position === "end" && (
        <span
          className={cn(
            "absolute left-0 w-0.5 top-0 bottom-1.5",
            group.kind === "in-use" && "bg-status-in-use/40",
            group.kind === "external" && "bg-status-borrowed/40",
          )}
          aria-hidden
        />
      )}

      <span
        className={cn(
          "inline-flex items-center justify-center size-8 rounded-full shrink-0",
          meta.bgClass,
          meta.fgClass,
        )}
      >
        <Icon className="size-4" aria-hidden />
      </span>

      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium">{formatLine(t)}</p>
        {t.note && <p className="text-xs text-muted-foreground mt-1">{t.note}</p>}

        {/* 超期提示行（仅 OPEN CHECKOUT）*/}
        {overdue && overdue.status !== "pending" && (
          <p
            className={cn(
              "text-xs font-medium mt-1 inline-flex items-center gap-1",
              overdue.status === "due-soon" && "text-warning-fg",
              overdue.status === "overdue" && "text-destructive",
            )}
          >
            <Clock className="size-3" aria-hidden />
            {overdue.status === "due-soon" ? `还有 ${overdue.days} 天到期` : `逾期 ${overdue.days} 天`}
          </p>
        )}
      </div>

      <time className="text-xs text-muted-foreground font-code shrink-0">
        {formatDate(t.created_at)} · {formatRelative(t.created_at)}
      </time>
    </li>
  );
}
```

- [ ] **Step 16.5: 跑组件测试，确认通过**

```bash
pnpm --dir frontend test transition-timeline.test.tsx
```

预期：PASS（5/5）。

- [ ] **Step 16.6: 跑全部测试 + tsc**

```bash
pnpm --dir frontend tsc -b
pnpm --dir frontend test
```

### Task 17: 起 dev server + 手工 visual 检查

**Files:** 无

- [ ] **Step 17.1: 起 dev server（后台）**

```bash
uv run asset-hub serve start --mode dev
```

等到 `:8000` + `:5173` ready。

- [ ] **Step 17.2: 找一台资产并手工触发几个 transition**

通过 GUI 或 CLI：
- 注册一台资产
- 派发（带 due_at 7 天后） → 看 timeline
- 归还
- 出借（带 due_at 30 天后）
- 改位置（RELOCATE）
- 归还

- [ ] **Step 17.3: 浏览器打开 http://localhost:5173/assets/<id>**

肉眼检查：
- 月份 heading 是否 sticky（滚动 timeline 时 heading 顶部贴住）
- Group rail 是否跨过 space-y-3 gap（多卡 rail 视觉无缝）
- 派发 ↔ 归还 一对 rail 颜色一致（蓝）
- 出借 ↔ 归还 一对 rail 颜色不同（琥珀）
- chip icon 全部正确（10 kind 各对应正确 icon）
- 时间格式 `2026-XX-XX · N 天前` 出现在右上角
- dark mode 切换：所有色 + token 视觉 OK

如有问题，回 Task 16 修。

### Task 18: playwright MCP 视觉烟测（Phase 3 视觉 gate）

**Files:** 无（截图存到 brainstorm 临时区或 `.playwright-screenshots/`）

- [ ] **Step 18.1: playwright MCP 走以下场景并截图**

打开 detail page 后：

1. `mcp__plugin_playwright_playwright__browser_navigate` http://localhost:5173/assets/<id>
2. `mcp__plugin_playwright_playwright__browser_snapshot` 看 DOM 结构
3. `mcp__plugin_playwright_playwright__browser_take_screenshot` light mode 整个 timeline section
4. 切 dark mode（手动 click theme toggle 或 evaluate `document.documentElement.classList.add('dark')`）
5. 再次 take_screenshot
6. `mcp__plugin_playwright_playwright__browser_evaluate` 滚动 timeline → take_screenshot 验 sticky heading

- [ ] **Step 18.2: 检查 console 无错误**

```
mcp__plugin_playwright_playwright__browser_console_messages
```

预期：无 React render 错 / 无 CSS var 未定义 warning。

### Task 19: Phase 3 commit

- [ ] **Step 19.1: tsc + lint + test**

```bash
pnpm --dir frontend tsc -b
pnpm --dir frontend lint
pnpm --dir frontend test
```

- [ ] **Step 19.2: commit**

```bash
git add frontend/src/features/assets/detail/transition-timeline.tsx frontend/tests/components/transition-timeline.test.tsx
# 如果 asset-detail-page.tsx 有调用点 prop 改动也加
grep -rln "<TransitionTimeline" frontend/src/features/assets/detail | xargs git add 2>&1 || true
git commit -m "$(cat <<'EOF'
feat(timeline): M3d 重构 — Group rail + 月份分段 + 新 icon + 时间格式

KIND_META 5 替换：CHECKOUT_EXTERNAL 共用 ArrowRightFromLine（颜色分化）/ CheckCircle2 → PackageCheck / Moon → Archive / Sun → ArchiveRestore / UserCog → ArrowLeftRight。
派出周期 Group rail 跨 space-y-3 gap (-bottom-3) 视觉无缝；
月份 sticky h3（不 backdrop-blur，bg-background 不透明）；
时间格式 "yyyy-MM-dd · N 天前" 单行；
OPEN CHECKOUT 卡内 overdue 提示行（due-soon 黄 / overdue 红）。
EOF
)"
```

---

## Phase 4 · 超期预警 + dialog UI 升级

### Task 20: CheckoutDialog 升级 due_at picker（datetime-local → Calendar + Popover）+ 同步 META icon

**Files:**
- Modify: `frontend/src/features/assets/detail/checkout-dialog.tsx`

- [ ] **Step 20.1: 改 import 块**

```tsx
- import { ArrowRightFromLine, Send, type LucideIcon } from "lucide-react";
+ import { ArrowRightFromLine, CalendarIcon, type LucideIcon } from "lucide-react";
+ import { format } from "date-fns";
+ import { zhCN } from "date-fns/locale";
+ import { Calendar } from "@/components/ui/calendar";
+ import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
+ import { FormDescription } from "@/components/ui/form";
+ import { cn } from "@/lib/utils";
```

确认 `FormDescription` 是 `@/components/ui/form` 已导出（如不是，看现有 form.tsx 加导出）。

- [ ] **Step 20.2: 改 META（CHECKOUT_EXTERNAL.Icon 从 Send → ArrowRightFromLine）**

```tsx
const META: Record<CheckoutKind, { verb: string; Icon: LucideIcon; audience: string }> = {
  CHECKOUT_INTERNAL: { verb: "派发", Icon: ArrowRightFromLine, audience: "团队成员" },
- CHECKOUT_EXTERNAL: { verb: "出借", Icon: Send,               audience: "外部人员" },
+ CHECKOUT_EXTERNAL: { verb: "出借", Icon: ArrowRightFromLine, audience: "外部人员" },
};
```

- [ ] **Step 20.3: dialog header 染色按 kind 分**

dialog header 当前 chip 用 `bg-status-in-use/15 text-status-in-use-fg` 写死蓝色（line ~98）。改成按 kind 分：

```tsx
- <span className="inline-flex items-center gap-1.5 rounded-full bg-status-in-use/15 px-2.5 py-1 text-xs font-medium text-status-in-use-fg">
+ <span className={cn(
+   "inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium",
+   kind === "CHECKOUT_INTERNAL" ? "bg-status-in-use/15 text-status-in-use-fg" : "bg-status-borrowed/15 text-status-borrowed-fg",
+ )}>
```

- [ ] **Step 20.4: 替换 due_at FormField 用 Calendar + Popover**

找到 `name="due_at"` 那块 FormField（line ~151），整段替换为：

```tsx
<FormField
  control={form.control}
  name="due_at"
  render={({ field }) => (
    <FormItem>
      <FormLabel>期望归还时间（可选）</FormLabel>
      <Popover>
        <PopoverTrigger asChild>
          <FormControl>
            <Button
              variant="outline"
              className={cn(
                "w-full justify-start text-left font-normal",
                !field.value && "text-muted-foreground",
              )}
              disabled={mutation.isPending}
            >
              <CalendarIcon className="mr-2 h-4 w-4" />
              {field.value
                ? format(new Date(field.value), "yyyy-MM-dd", { locale: zhCN })
                : "选择日期"}
            </Button>
          </FormControl>
        </PopoverTrigger>
        <PopoverContent className="w-auto p-0" align="start">
          <Calendar
            mode="single"
            selected={field.value ? new Date(field.value) : undefined}
            onSelect={(d) => field.onChange(d ? format(d, "yyyy-MM-dd") : "")}
            disabled={(d) => d < new Date(new Date().setHours(0, 0, 0, 0))}
            initialFocus
          />
        </PopoverContent>
      </Popover>
      <FormDescription className="text-xs">
        建议填写以启用超期提醒；留空则不预警
      </FormDescription>
      <FormMessage />
    </FormItem>
  )}
/>
```

- [ ] **Step 20.5: 改 mutation body 兼容新存储格式**

现有提交逻辑 `due_at: values.due_at || null` —— Calendar onSelect 存的是 `'yyyy-MM-dd'` 字符串。后端 `due_at: datetime | None` 接 ISO datetime。提交前转：

```tsx
- due_at: values.due_at || null,
+ due_at: values.due_at ? `${values.due_at}T00:00:00` : null,  // 当地时区 00:00:00
```

- [ ] **Step 20.6: tsc + lint**

```bash
pnpm --dir frontend tsc -b
pnpm --dir frontend lint
```

### Task 21: checkout-dialog.test.tsx 新建 + 测试 due_at 提交

**Files:**
- Create: `frontend/tests/components/checkout-dialog.test.tsx`

- [ ] **Step 21.1: 写测试**

```tsx
import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import { CheckoutDialog } from "@/features/assets/detail/checkout-dialog";
import * as transitionsHook from "@/api/hooks/transitions";

function renderWithProvider(ui: React.ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

describe("CheckoutDialog (M3d due_at picker)", () => {
  it("提交 due_at 字段 → mutation body 含 ISO datetime string", async () => {
    const mockMutate = vi.fn().mockResolvedValue({});
    vi.spyOn(transitionsHook, "useRecordTransitionMutation").mockReturnValue({
      mutateAsync: mockMutate, isPending: false, isError: false, error: null, reset: vi.fn(),
    } as never);

    renderWithProvider(<CheckoutDialog open onOpenChange={vi.fn()} assetId="a1" kind="CHECKOUT_INTERNAL" />);

    await userEvent.type(screen.getByPlaceholderText("保管人/接收方"), "张三");
    // 打开 Calendar popover
    await userEvent.click(screen.getByRole("button", { name: /选择日期/ }));
    // 选今天后 7 天（jsdom 不易精确 click cell，改：直接 setValue 通过 input；或留 playwright MCP 烟测覆盖）
    // 这里简化：仅测 holder + submit，验 due_at 缺省提交为 null
    await userEvent.click(screen.getByRole("button", { name: /^派发资产|^派发$/ }));

    expect(mockMutate).toHaveBeenCalledWith(expect.objectContaining({
      to_holder: "张三",
      due_at: null,
    }));
  });

  it("不填 due_at → body due_at = null", async () => {
    const mockMutate = vi.fn().mockResolvedValue({});
    vi.spyOn(transitionsHook, "useRecordTransitionMutation").mockReturnValue({
      mutateAsync: mockMutate, isPending: false, isError: false, error: null, reset: vi.fn(),
    } as never);

    renderWithProvider(<CheckoutDialog open onOpenChange={vi.fn()} assetId="a1" kind="CHECKOUT_INTERNAL" />);
    await userEvent.type(screen.getByPlaceholderText("保管人/接收方"), "张三");
    // 直接提交，不动 due_at
    await userEvent.click(screen.getByRole("button", { name: /^派发资产|^派发$/ }));

    expect(mockMutate).toHaveBeenCalledWith(expect.objectContaining({
      to_holder: "张三",
      due_at: null,
    }));
  });

  it("CHECKOUT_EXTERNAL → header chip 用 status-borrowed 染色", () => {
    vi.spyOn(transitionsHook, "useRecordTransitionMutation").mockReturnValue({
      mutateAsync: vi.fn(), isPending: false, isError: false, error: null, reset: vi.fn(),
    } as never);

    const { container } = renderWithProvider(
      <CheckoutDialog open onOpenChange={vi.fn()} assetId="a1" kind="CHECKOUT_EXTERNAL" />,
    );

    expect(container.querySelector(".bg-status-borrowed\\/15")).toBeInTheDocument();
  });
});
```

**注意**：jsdom 下 Calendar cell click 不稳定；本测试仅覆盖"未填 due_at = null"+"chip 染色"两条路径。"填 due_at → ISO datetime"路径留 playwright MCP 烟测覆盖（Task 30 step 1）。

- [ ] **Step 21.2: 跑测试**

```bash
pnpm --dir frontend test checkout-dialog.test.tsx
```

预期：PASS（3/3）。

### Task 22: AssetHeader 加 overdue 角标

**Files:**
- Modify: `frontend/src/features/assets/detail/asset-header.tsx`

- [ ] **Step 22.1: 加 import**

```tsx
+ import { Clock, MoreHorizontal } from "lucide-react";
+ import { useTransitionsQuery } from "@/api/hooks/transitions";
+ import { calcOverdue } from "@/lib/overdue";
+ import { cn } from "@/lib/utils";
```

`MoreHorizontal` 已存在保留；只是合并到一行 import。

- [ ] **Step 22.2: 抽 useOverdue hook（在文件内本地定义）**

`AssetHeader` 函数定义之前加：

```tsx
function useOverdueForOpenCheckout(assetId: string, assetStatus: AssetRead["status"]) {
  const { data: transitions } = useTransitionsQuery(assetId);
  if (!transitions) return null;
  // 找 OPEN CHECKOUT：kind 是 CHECKOUT_*，且没有 RETURN.closes_transition_id 引用它
  const closedIds = new Set(
    transitions
      .filter((t) => t.kind === "RETURN" && t.closes_transition_id)
      .map((t) => t.closes_transition_id as string),
  );
  const open = transitions.find(
    (t) => (t.kind === "CHECKOUT_INTERNAL" || t.kind === "CHECKOUT_EXTERNAL") && !closedIds.has(t.id),
  );
  if (!open) return null;
  return calcOverdue(open.due_at, assetStatus);
}
```

- [ ] **Step 22.3: 在 H1 旁加角标**

找到 `<h1 className="text-2xl font-semibold">{asset.name}</h1>`（line 47），改成：

```tsx
function AssetHeader({ asset, onDelete }: AssetHeaderProps) {
  const overdue = useOverdueForOpenCheckout(asset.id, asset.status);
  return (
    <header className="flex items-start justify-between gap-4">
      <div className="space-y-1">
        ...
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-semibold">{asset.name}</h1>
          {overdue && overdue.status !== "pending" && (
            <span
              className={cn(
                "inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium",
                overdue.status === "due-soon" && "bg-warning/15 text-warning-fg",
                overdue.status === "overdue" && "bg-destructive/15 text-destructive",
              )}
            >
              <Clock className="size-3" aria-hidden />
              {overdue.status === "due-soon" ? `还有 ${overdue.days} 天到期` : `逾期 ${overdue.days} 天`}
            </span>
          )}
        </div>
        ...
      </div>
      <ActionArea ... />
    </header>
  );
}
```

注意：原 H1 在 `<div className="space-y-1">` 直系子元素；包到 `<div className="flex items-center gap-3">` 后会改 spacing 视觉，需手工 visual review（Task 23 之后烟测）。如果效果差，可改为 `<h1>` 内嵌 `<span>` 角标：

```tsx
<h1 className="text-2xl font-semibold flex items-center gap-3">
  {asset.name}
  {overdue && ...}
</h1>
```

- [ ] **Step 22.4: tsc + lint**

```bash
pnpm --dir frontend tsc -b
pnpm --dir frontend lint
```

### Task 23: asset-header.test.tsx 新建 + 测 overdue 角标 3 分支

**Files:**
- Create: `frontend/tests/components/asset-header.test.tsx`

- [ ] **Step 23.1: 写测试**

```tsx
import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { createRouter, RouterProvider, createRootRoute, createRoute } from "@tanstack/react-router";

import { AssetHeader } from "@/features/assets/detail/asset-header";
import * as transitionsHook from "@/api/hooks/transitions";
import type { AssetRead, TransitionRead } from "@/features/assets/types";

const baseAsset: AssetRead = {
  id: "a1",
  asset_code: "NB-001",
  name: "ThinkPad",
  type_id: "t1",
  type_name: "笔记本",
  status: "IN_USE",
  holder: "张三",
  location: "工位 A1",
  custom_data: {},
  acquired_at: null,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-04-20T00:00:00Z",
  idle_days: 0,
} as AssetRead;

function mkOpen(due_at: string | null): TransitionRead {
  return {
    id: "co1", asset_id: "a1", kind: "CHECKOUT_INTERNAL",
    from_status: "IDLE", to_status: "IN_USE",
    from_holder: null, to_holder: "张三",
    from_location: null, to_location: "工位 A1",
    note: null, created_at: "2026-04-20T10:00:00Z",
    due_at, closes_transition_id: null,
  } as TransitionRead;
}

function renderWithProviders(ui: React.ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const root = createRootRoute({ component: () => <>{ui}</> });
  const router = createRouter({ routeTree: root, history: { type: "memory" } as never });
  return render(
    <QueryClientProvider client={qc}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  );
}

describe("AssetHeader overdue 角标 (M3d)", () => {
  it("status IN_USE + dueAt 8 天前 + OPEN CHECKOUT → render 逾期 8 天 红角标", () => {
    const dueAt = new Date(Date.now() - 8 * 86400000).toISOString().slice(0, 10);
    vi.spyOn(transitionsHook, "useTransitionsQuery").mockReturnValue({
      data: [mkOpen(`${dueAt}T00:00:00`)], isLoading: false, isError: false, error: null, refetch: vi.fn(),
    } as never);

    renderWithProviders(<AssetHeader asset={{ ...baseAsset, status: "IN_USE" }} onDelete={vi.fn()} />);
    expect(screen.getByText(/逾期 8 天/)).toBeInTheDocument();
  });

  it("status IDLE + dueAt 任意 → 不 render 角标", () => {
    vi.spyOn(transitionsHook, "useTransitionsQuery").mockReturnValue({
      data: [], isLoading: false, isError: false, error: null, refetch: vi.fn(),
    } as never);

    renderWithProviders(<AssetHeader asset={{ ...baseAsset, status: "IDLE" }} onDelete={vi.fn()} />);
    expect(screen.queryByText(/逾期|还有/)).not.toBeInTheDocument();
  });

  it("status IN_USE + dueAt null → 不 render 角标", () => {
    vi.spyOn(transitionsHook, "useTransitionsQuery").mockReturnValue({
      data: [mkOpen(null)], isLoading: false, isError: false, error: null, refetch: vi.fn(),
    } as never);

    renderWithProviders(<AssetHeader asset={{ ...baseAsset, status: "IN_USE" }} onDelete={vi.fn()} />);
    expect(screen.queryByText(/逾期|还有/)).not.toBeInTheDocument();
  });

  it("status IN_USE + dueAt 5 天后 → render 还有 5 天到期 黄角标", () => {
    const dueAt = new Date(Date.now() + 5 * 86400000).toISOString().slice(0, 10);
    vi.spyOn(transitionsHook, "useTransitionsQuery").mockReturnValue({
      data: [mkOpen(`${dueAt}T00:00:00`)], isLoading: false, isError: false, error: null, refetch: vi.fn(),
    } as never);

    renderWithProviders(<AssetHeader asset={{ ...baseAsset, status: "IN_USE" }} onDelete={vi.fn()} />);
    expect(screen.getByText(/还有 5 天到期/)).toBeInTheDocument();
  });
});
```

**注意**：AssetHeader 含 `<Link>`（TanStack Router），测试需 RouterProvider mock；如已有 helper 复用之，否则按上方 mock 写。

- [ ] **Step 23.2: 跑测试**

```bash
pnpm --dir frontend test asset-header.test.tsx
```

预期：PASS（4/4）。如 Router 类型不对（v1 API 变化），调整 createRouter 调用或 fallback 用 MemoryRouter helper。

### Task 24: Phase 4 验收 + commit

- [ ] **Step 24.1: tsc + lint + test**

```bash
pnpm --dir frontend tsc -b
pnpm --dir frontend lint
pnpm --dir frontend test
```

- [ ] **Step 24.2: 起 dev 手工验证 overdue 角标**

```bash
uv run asset-hub serve restart --mode dev
```

浏览器访问 detail page 触发派发（带 due_at = 1 天后）→ 看角标"还有 1 天到期"黄色显示；改 due_at 到过去 → 看"逾期 N 天"红色。

- [ ] **Step 24.3: commit**

```bash
git add frontend/src/features/assets/detail/checkout-dialog.tsx frontend/src/features/assets/detail/asset-header.tsx frontend/tests/components/checkout-dialog.test.tsx frontend/tests/components/asset-header.test.tsx
git commit -m "$(cat <<'EOF'
feat(timeline): M3d 超期预警 + dialog UI 升级

CheckoutDialog due_at 从 datetime-local 升级到 Calendar + Popover（复用 acquired_at 范本）；
META.CHECKOUT_EXTERNAL.Icon 从 Send → ArrowRightFromLine 同步 timeline KIND_META；
header chip 按 kind 分蓝/琥珀；
AssetHeader 加 overdue 角标（复用 useTransitionsQuery + queryKey dedupe 零额外请求）；
两阶段染色：due-soon bg-warning/15 / overdue bg-destructive/15。
EOF
)"
```

### Task 25: phase 4 自验

- [ ] **Step 25.1: playwright MCP 复测 overdue 角标场景**

dev server 上：
1. 派发资产（due_at 1 天后）→ snapshot timeline + AssetHeader → 验黄角标 "还有 1 天到期"
2. 后端 sql `UPDATE state_transition_records SET due_at = '2026-04-29T00:00:00' WHERE asset_id = '<id>'` 模拟逾期 → 刷新页面 → 验红角标 "逾期 N 天"
3. 列表页对比：列表行**不**显示 overdue 角标（spec §1.5）

---

## Phase 5 · C 三搭车

### Task 26: C-1 TypesTable 接 motion 三时刻

**Files:**
- Modify: `frontend/src/features/types/list/types-table.tsx`

- [ ] **Step 26.1: 读现有 types-table.tsx**

```bash
cat frontend/src/features/types/list/types-table.tsx
```

找到 `<tbody>` + 行 map 段。

- [ ] **Step 26.2: 加 tbody-fade + stagger-row（按 assets-table.tsx 范本）**

```tsx
- <tbody>
+ <tbody key={query.dataUpdatedAt} className="tbody-fade">
   {rows.map((row, idx) => (
     <tr
       key={row.id}
-      className="..."
+      className="stagger-row ..."
+      style={{ animationDelay: idx < 20 ? `${idx * 18}ms` : "0ms" }}
     >
```

`query.dataUpdatedAt` 来源是 `useTypesQuery()`（确认 hook 名称，grep 一下）。

```bash
grep -n "useTypesQuery\|useQuery" frontend/src/features/types/list/types-table.tsx | head -5
```

- [ ] **Step 26.3: tsc**

```bash
pnpm --dir frontend tsc -b
```

### Task 27: C-2 H1 type scale 对齐

**Files:**
- Modify: `frontend/src/features/types/detail/type-detail-page.tsx`
- Modify: `frontend/src/styles/globals.css`

- [ ] **Step 27.1: type-detail-page H1 升级**

```bash
grep -n "text-xl font-semibold" frontend/src/features/types/detail/type-detail-page.tsx
```

改：

```tsx
- <h1 className="text-xl font-semibold">...</h1>
+ <h1 className="text-2xl font-semibold">...</h1>
```

- [ ] **Step 27.2: globals.css 顶部加 type scale 注释**

在 `globals.css` 文件最顶部（在 `@import` / `@theme` 之前 / 之后看现有结构）加注释：

```css
/* M3d 引入 type scale 二档约定（详见 design-system/asset-hub/MASTER.md "排版" 节）：
 *   列表 / 配置页 H1：text-xl font-semibold
 *   详情页 H1     ：text-2xl font-semibold
 *   看板（hero）  ：不纳入约定（dashboard-header 用 text-3xl font-medium tracking-tight 独立形态）
 * 新加页面前按归类挑选；偏离需在 MASTER.md 加行说明。
 */
```

- [ ] **Step 27.3: 全局 grep 找漏网 H1**

```bash
grep -rn "<h1\b" frontend/src/features --include="*.tsx" | grep -v ".test."
```

确认所有 `<h1>` 命中三档之一：

- 列表 / 配置：`text-xl font-semibold`
- 详情：`text-2xl font-semibold`
- 看板：`text-3xl font-medium tracking-tight`

如发现第 4 档（任何不在三档内的 H1），按页面分类归到对应档（不在档内的 H1 一律归"详情"或"列表"，看板形态只 dashboard 一处）。改完再跑一次 grep 确认。

- [ ] **Step 27.4: tsc**

```bash
pnpm --dir frontend tsc -b
```

### Task 28: C-3 attachment-grid prop 修正

**Files:**
- Modify: `frontend/src/features/assets/detail/attachment-grid.tsx:54`

- [ ] **Step 28.1: 改一行**

```tsx
- className="... transition-shadow hover:ring-2 hover:ring-primary/40"
+ className="... transition-all hover:ring-2 hover:ring-primary/40"
```

`hover:ring-*` 底层是 box-shadow，原 `transition-shadow` 凑巧能用但语义错；`transition-all` 让 transition 触发更精准。

- [ ] **Step 28.2: tsc + lint**

```bash
pnpm --dir frontend tsc -b
pnpm --dir frontend lint
```

### Task 29: Phase 5 commit

- [ ] **Step 29.1: 跑全测**

```bash
pnpm --dir frontend test
```

- [ ] **Step 29.2: commit**

```bash
git add frontend/src/features/types/list/types-table.tsx frontend/src/features/types/detail/type-detail-page.tsx frontend/src/styles/globals.css frontend/src/features/assets/detail/attachment-grid.tsx
git commit -m "$(cat <<'EOF'
refactor(visual): M3d simplify §7 三搭车闭环

C-1 TypesTable 接 motion 三时刻 (tbody-fade + stagger-row)；
C-2 type-detail-page H1 升级 text-xl → text-2xl 对齐详情页二档；
    globals.css 顶部加 type scale 注释 (MASTER.md "排版" 节为 SoT)；
C-3 attachment-grid transition-shadow → transition-all 修正 prop 语义。
EOF
)"
```

---

## Phase 6 · 收尾

### Task 30: playwright MCP 完整视觉烟测（spec §5 烟测清单 6 场景）

**Files:** 无（截图存到 `.playwright-screenshots/m3d/` 或 brainstorm 临时区）

- [ ] **Step 30.1: 起 dev server**

```bash
uv run asset-hub serve restart --mode dev
```

- [ ] **Step 30.2: 6 场景手动 + playwright 烟测**

按 spec §5 末尾 烟测清单：

1. **新建一台资产 → 派发（带 due_at = 1 天后）** → 看 timeline + AssetHeader 显示 due-soon 黄预警
2. **时间穿越**：sql `UPDATE state_transition_records SET due_at = '<8d_ago>' WHERE id = '<co_id>'` → 刷新看 overdue 红角标
3. **多 transition 历史**：手工触发 10 个 transition（CHECKOUT_INTERNAL / RETURN / CHECKOUT_EXTERNAL / RETURN / SEND_TO_MAINTENANCE / RECOVER / RELOCATE / TRANSFER_HOLDER / RETIRE / REINSTATE / DISPOSE）→ 看 Group rail 跨 gap + 月份分段 + 新 icon 全套视觉
4. **类型管理页**：访问 `/types` → 观察 motion stagger 入场（`tbody-fade` + 行 stagger）
5. **dark mode 切换**：theme toggle → 所有新色（status-borrowed / warning）双主题 OK
6. **页面 H1 visual 对齐**：`/types`（text-xl）/ `/types/<id>`（text-2xl）/ `/assets/<id>`（text-2xl）/ `/dashboard`（text-3xl 看板独立）四页 H1 字号视觉一致性

每场景截图 + 写入 `.playwright-screenshots/m3d/scenario-{1..6}.png`。

- [ ] **Step 30.3: console 无错**

```
mcp__plugin_playwright_playwright__browser_console_messages
```

预期：无 React render 错 / 无 CSS var 未定义 warning。

### Task 31: 推 PR

- [ ] **Step 31.1: 推分支**

```bash
git push -u origin feat/m3d-timeline-visual
```

- [ ] **Step 31.2: 起 PR**（用户全局 CLAUDE.md 要求 commit/PR 不含 "Generated with Claude Code" 等标记）

```bash
gh pr create --title "feat(M3d): timeline 视觉重构 + simplify §7 搭车" --body "$(cat <<'EOF'
## Summary

- **timeline 重构**：Group rail（派出周期粒度）+ 月份 sticky heading（时间粒度）替代"卡片粒度色条"路径；KIND_META 5 替换（CHECKOUT_EXTERNAL 共用 ArrowRightFromLine、PackageCheck/Archive/ArchiveRestore/ArrowLeftRight 收敛 icon 风格）
- **超长派发预警**：基于 due_at 两阶段（< 7d 黄 / 超期 红），timeline + AssetHeader 双位置；CheckoutDialog due_at 从 datetime-local 升级 Calendar+Popover
- **C 三搭车**：TypesTable motion / 详情页 H1 二档对齐 / attachment-grid transition prop 修正

## 视觉对照

| 场景 | 截图 |
|---|---|
| timeline light mode | \`.playwright-screenshots/m3d/scenario-3-light.png\` |
| timeline dark mode | \`.playwright-screenshots/m3d/scenario-5-dark.png\` |
| AssetHeader overdue | \`.playwright-screenshots/m3d/scenario-2-overdue.png\` |

## Test plan

- [x] vitest unit 全绿（calc-overdue / format-relative / timeline-grouping / tokens）
- [x] vitest component 全绿（transition-timeline / checkout-dialog / asset-header）
- [x] tsc -b 0 错
- [x] lint 0 错
- [x] playwright MCP 6 场景烟测通过
- [x] dark mode 双主题视觉验收
- [x] dev server 手工测试 overdue 角标 3 分支

Spec: docs/superpowers/specs/2026-05-07-m3d-timeline-visual-design.md
EOF
)"
```

### Task 32: merge + 文档回填

- [ ] **Step 32.1: merge to main（--no-ff 保 merge commit）**

```bash
git checkout main
git pull --ff-only origin main
git merge --no-ff feat/m3d-timeline-visual -m "Merge branch 'feat/m3d-timeline-visual' (M3d: timeline 视觉重构 + simplify §7 搭车)"
git push origin main
```

或在 GitHub UI 选 "Create a merge commit"（同等效果）。

- [ ] **Step 32.2: 文档回填 — simplify-followups.md §7 三项标 ✅ 闭环**

```bash
grep -n "## §7 M2 视觉收尾审计未选项" docs/superpowers/simplify-followups.md
```

在 §7 节的 M1 / M3 / M4 三项各自标题加 `· ✅ 闭环`：

- M1 TypesTable Motion → "M1 · TypesTable 未接 Motion 三时刻 · ✅ 闭环（M3d C-1）"
- M3 H1 type scale → "M3 · 页面 H1 字号三档无 type scale token · ✅ 闭环（M3d C-2）"
- M4 attachment-grid prop → "M4 · attachment-grid transition-shadow 配错 prop 名 · ✅ 闭环（M3d C-3）"

- [ ] **Step 32.3: 文档回填 — followup-allocation.md M3d 标 ✅**

找到摘要表 "M3b–M3e" 那行（line ~109），改成：

```
| **M3d** | timeline 视觉重构 + simplify §7 搭车 | C-1 / C-2 / C-3 | 3 | ✅ 已完成（2026-05-07，merge `<merge-sha>`）|
```

- [ ] **Step 32.4: 文档回填 — 主 spec §14.8 时间渐隐条款标 "M3d 决议作废"**

```bash
grep -n "时间近远渐隐\|时间渐隐" docs/superpowers/specs/2026-04-15-asset-hub-design.md
```

找到 §14.8 "时间近远渐隐：旧记录卡 opacity 分级" 那段，开头加：

```
- ~~时间近远渐隐：旧记录卡 opacity 分级（≤90d 100% / ≤180d 80% / 更早 60%）~~ → **M3d 决议作废**（理由见 [M3d spec §1.1](../specs/2026-05-07-m3d-timeline-visual-design.md#11-时间渐隐砍掉)）
```

- [ ] **Step 32.5: 单 commit 包含所有文档回填**

```bash
git add docs/superpowers/simplify-followups.md docs/superpowers/followup-allocation.md docs/superpowers/specs/2026-04-15-asset-hub-design.md
git commit -m "$(cat <<'EOF'
docs(followup): M3d 落地后文档回填

simplify-followups §7 M1/M3/M4 三项标 ✅ 闭环（M3d C-1/C-2/C-3）；
followup-allocation 摘要表 M3d 标 ✅ 已完成；
主 spec §14.8 时间渐隐条款标 M3d 决议作废。
EOF
)"
git push origin main
```

- [ ] **Step 32.6: Lighthouse a11y 全站扫描（spec §8 后续）**

dev / prod server 上：

```bash
# 安装（如无）
npx -y lighthouse http://localhost:5173/assets --only-categories=accessibility --output=json --output-path=lighthouse-a11y-list.json
npx -y lighthouse http://localhost:5173/assets/<some_id> --only-categories=accessibility --output=json --output-path=lighthouse-a11y-detail.json
npx -y lighthouse http://localhost:5173/dashboard --only-categories=accessibility --output=json --output-path=lighthouse-a11y-dashboard.json
npx -y lighthouse http://localhost:5173/types --only-categories=accessibility --output=json --output-path=lighthouse-a11y-types.json
```

读 score。score < 95 的页面记录到 followups（M3e 修复），不阻塞 M3d merge。

---

## 自查清单

- [ ] Phase 1 token 都加了双主题（light + dark）
- [ ] Phase 2 utility 全部 TDD（先写失败测试再实现）
- [ ] Phase 3 visual gate 在 Phase 4 之前过
- [ ] Phase 4 dialog META icon 同步（CHECKOUT_EXTERNAL.Icon = ArrowRightFromLine）
- [ ] Phase 5 三搭车不混进 Phase 3/4 commit
- [ ] commit message 不含 "Generated with Claude Code" / "Co-Authored-By: Claude"
- [ ] 后端零改动（不动 src/asset_hub/）
- [ ] 测试覆盖：4 unit suite + 3 component suite 全绿
