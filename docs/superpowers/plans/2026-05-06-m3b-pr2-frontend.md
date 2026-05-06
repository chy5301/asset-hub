# M3b PR-2 实施计划：前端 /dashboard 集成 + D1/H4/C3 闭环

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** M3b PR-2 落地——`/dashboard` 路由 + 4 图 + 4 套 Skeleton + 4 个差异化空态 + page load staggered reveal motion；同期闭环 D1（全前端 generated import → 业务 alias 层）+ H4（独立 `frontend/src/api/types.ts` 抽 `OpenapiFetchResult<T>`）+ C3 前端切（删 `useAssetTypesQuery()`）。

**Architecture:** D-原版布局（左 60% 闲置榜全高 / 右 40% 三段）；shadcn/ui charts (Recharts) 复用 design-system OKLCH token；`useStatsQuery` 接 PR-1 已落 `/api/stats`；4 图 customization 红线全落；保管人禁用 horizontal bar chart。

**Tech Stack:** React 19 / TanStack Router / TanStack Query / shadcn/ui / Tailwind v4 / TypeScript 6 / openapi-fetch / Framer Motion / vitest / MSW / Playwright MCP。

**Spec:** [`docs/superpowers/specs/2026-05-06-m3b-dashboard-stats-design.md`](../specs/2026-05-06-m3b-dashboard-stats-design.md)

**前置约束**：

- **PR-1 必须已合并到 main**——否则前端 `pnpm gen:api` 拉不到新 stats schema
- main 上 `frontend/src/lib/error.ts::unwrap` 现有签名（spec / 之前对话误称 `api/error.ts`）
- `unwrap` 实际位于 `frontend/src/lib/error.ts`，PR-2 内迁到 `frontend/src/api/types.ts` + 简化签名
- 项目用 Tailwind v4——shadcn chart 文档多 v3 示例，spike 步骤需验证兼容
- M3a 已落 5 态 status OKLCH token + checkout-internal/external 派出 token；本 PR 复用，仅新增 `--chart-1..6` 6 槽 token

**任务总览**（16 任务）：

1. PR-1 schema 同步（`pnpm gen:api`）
2. H4 — 建 `api/types.ts` `OpenapiFetchResult<T>` + 简化 `unwrap` 签名
3. D1 — 建 `features/assets/types.ts` 业务 alias 层
4. D1 — 全前端 7 文件 grep replace + `tsc -b` 校验
5. C3 前端切 — `asset-detail-page.tsx` 删 `useAssetTypesQuery()`
6. design-system tokens — `--chart-1..6` 6 槽错位 hue + atmosphere 变量
7. shadcn chart spike + 决议 wrapper/裸用
8. dashboard 路由 + search-schema
9. `useStatsQuery` hook + MSW handlers + 4 空态判定纯函数
10. 看板顶栏（h1 + 副标 + inline pill toggle 基线对齐）
11. dashboard-page D-原版 grid 容器 + atmosphere
12. `IdleTopBarChart` + `TypeDistributionChart`（左主锚 + 右上 donut）
13. `StatusDistributionChart` + `HolderLeaderboard`（右中 stacked bar + 右下 leaderboard）
14. 4 套 Skeleton 形态匹配 + 4 个空态组件
15. page load Motion 编排（Framer Motion staggered reveal）
16. 入口接入 + Playwright MCP 烟测 + PR-2 验收

---

## Task 1: 同步 PR-1 schema

**Files:**
- Modify: `frontend/src/api/generated/schema.d.ts`（自动生成）
- Verify: dev server 后端 `:8000` 在跑

- [ ] **Step 1.1: 启动后端 dev server**

```bash
uv run uvicorn asset_hub.api.app:app --reload &
# 等待 ~3s 后端就绪
curl -s http://localhost:8000/openapi.json | head -c 200
```

预期：返 OpenAPI JSON 头部。

- [ ] **Step 1.2: 拉新 schema**

```bash
pnpm --dir frontend gen:api
```

- [ ] **Step 1.3: 确认 stats schema 已生成**

```bash
grep -n "StatsRead\|StatsSummary\|stats" frontend/src/api/generated/schema.d.ts | head -10
```

预期：能看到 `/api/stats` 路径 + `StatsRead` schema。

- [ ] **Step 1.4: tsc 校验**

```bash
pnpm --dir frontend tsc -b
```

预期：无 type 错（schema 是新增，不打破现有代码）。

- [ ] **Step 1.5: 提交**

```bash
git add frontend/src/api/generated/schema.d.ts
git commit -m "chore(frontend): sync OpenAPI schema with PR-1 stats endpoint

新增 GET /api/stats 与 StatsRead/StatsSummary 等 schema；
GET /api/assets 加 sort_by/sort_order/limit/offset 参数。"
```

---

## Task 2: H4 — 建 `api/types.ts` 抽 `OpenapiFetchResult<T>`

**Files:**
- Create: `frontend/src/api/types.ts`
- Modify: `frontend/src/lib/error.ts`（删 unwrap，迁过去）
- Modify: 任何 import `unwrap` from `lib/error` 的文件 → import from `api/types`

- [ ] **Step 2.1: 找 unwrap 当前 caller**

```bash
grep -rn "from '@/lib/error'" frontend/src 2>&1
grep -rn 'unwrap[(<]' frontend/src 2>&1 | head -20
```

记录所有 caller 文件路径，下面要批量改 import。

- [ ] **Step 2.2: 写 `api/types.ts`**

```typescript
// frontend/src/api/types.ts
/**
 * API 客户端层公共类型 + 工具.
 *
 * 此文件是 spec §H4 决议产物：
 * - OpenapiFetchResult<T>：统一 openapi-fetch 返回形状
 * - unwrap()：从 client.ts 工具迁移到此，签名简化
 *
 * 与业务 alias 层 (features/assets/types.ts, spec §D1) 关注点分离：
 * - 此文件 = openapi-fetch 通用包装（与具体 feature 无关）
 * - features/assets/types.ts = 业务 DTO alias
 */
import type { components } from "./generated/schema";

import { toHttpError } from "@/lib/error";

/** openapi-fetch 调用的统一返回形状 (data | error + response). */
export type OpenapiFetchResult<T> = {
  data?: T;
  error?: unknown;
  response: Response;
};

/** 拆 OpenapiFetchResult，成功返 data；失败抛 HttpErrorShape (toHttpError 统一映射). */
export function unwrap<T>(result: OpenapiFetchResult<T>): T {
  if (result.error || !result.data) {
    throw toHttpError(result);
  }
  return result.data;
}

/** 同 unwrap，但 204/无 body 端点用. */
export function unwrapVoid(
  result: { error?: unknown; response: Response }
): void {
  if (result.error) {
    throw toHttpError(result);
  }
}

/** 业务 alias 层之外、API 客户端通用的 schema 类型重导出. */
export type ApiSchema = components["schemas"];
```

- [ ] **Step 2.3: 简化 `lib/error.ts`**

```typescript
// frontend/src/lib/error.ts 改后只剩 toHttpError + HttpErrorShape；删 unwrap/unwrapVoid
// 文件顶部不变 (HttpErrorShape interface, toHttpError 函数)；
// 删除原 42-58 行的 unwrap 与 unwrapVoid（已迁到 api/types.ts）
```

具体删除范围：

```diff
-/** Wrap openapi-fetch 的 { data, error, response } 响应，失败时抛 HttpErrorShape。 */
-export function unwrap<T>(result: { data?: T; error?: unknown; response: Response }): T {
-  if (result.error || !result.data) { throw toHttpError(result); }
-  return result.data;
-}
-
-/** 同 `unwrap`，但用于 204/无 body 端点：成功时返回 void，失败时抛 HttpErrorShape。 */
-export function unwrapVoid(result: { error?: unknown; response: Response }): void {
-  if (result.error) { throw toHttpError(result); }
-}
```

- [ ] **Step 2.4: 批量改 caller import**

对 Step 2.1 找到的每个 `unwrap` caller 文件：

```typescript
// 原：
import { unwrap } from "@/lib/error";
// 改：
import { unwrap } from "@/api/types";
```

`unwrapVoid` 同理。

- [ ] **Step 2.5: tsc 校验**

```bash
pnpm --dir frontend tsc -b
```

预期：无 type 错。

- [ ] **Step 2.6: 跑前端单测确保兼容**

```bash
pnpm --dir frontend test
```

预期：全 PASS（unwrap 行为未变，仅迁位）。

- [ ] **Step 2.7: 提交**

```bash
git add frontend/src/api/types.ts frontend/src/lib/error.ts frontend/src/**/*.ts frontend/src/**/*.tsx
git commit -m "refactor(api): H4 抽 OpenapiFetchResult<T> + 迁 unwrap 至 api/types.ts

spec §H4 决议：unwrap/unwrapVoid 从 lib/error.ts 迁到 api/types.ts；
新增 OpenapiFetchResult<T> 类型让签名摆脱 inline 联合形态。
lib/error.ts 现仅含 toHttpError 与 HttpErrorShape。"
```

---

## Task 3: D1 — 建 `features/assets/types.ts` 业务 alias 层

**Files:**
- Create: `frontend/src/features/assets/types.ts`

- [ ] **Step 3.1: 写 alias 层**

```typescript
// frontend/src/features/assets/types.ts
/**
 * 业务 DTO alias 层（spec §D1 决议）.
 *
 * 全前端业务代码 import 业务类型只走此文件，不再直接 import generated schema.
 * 未来 codegen 工具切换 / 后端 DTO 改名 → 仅改此文件，业务代码 0 churn.
 *
 * 此文件与 api/types.ts (spec §H4) 关注点分离：
 * - api/types.ts = API 客户端通用包装（OpenapiFetchResult/unwrap）
 * - 此文件 = 业务 DTO 重命名导出
 */
import type { components } from "@/api/generated/schema";

type S = components["schemas"];

// === Asset ===
export type AssetRead = S["AssetRead"];
export type AssetCreate = S["AssetCreate"];
export type AssetUpdate = S["AssetUpdate"];
export type AssetStatus = S["AssetStatus"];

// === AssetType ===
export type AssetTypeRead = S["AssetTypeRead"];
export type AssetTypeCreate = S["AssetTypeCreate"];
export type AssetTypeUpdate = S["AssetTypeUpdate"];
export type AssetTypeFieldDef = S["AssetTypeFieldDef"];
export type FieldType = S["FieldType"];

// === Transition ===
export type TransitionRead = S["TransitionRead"];
export type TransitionKind = S["TransitionKind"];
export type TransitionCreate = S["TransitionCreate"];

// === Attachment ===
export type AttachmentRead = S["AttachmentRead"];

// === Stats (M3b 新) ===
export type StatsRead = S["StatsRead"];
export type StatsSummary = S["StatsSummary"];
export type IdleTopItem = S["IdleTopItem"];
export type HolderRankingItem = S["HolderRankingItem"];
export type TypeDistributionItem = S["TypeDistributionItem"];
```

> 实际字段名以 `pnpm gen:api` 生成的 schema.d.ts 为准；如有差异（如 `AssetTypeFieldDef` 是否在 schema 里），按生成结果调整。

- [ ] **Step 3.2: 快速 verify alias 都能解析**

```bash
pnpm --dir frontend tsc -b
```

预期：无错。

- [ ] **Step 3.3: 提交**

```bash
git add frontend/src/features/assets/types.ts
git commit -m "feat(types): D1 业务 alias 层骨架

re-export 全部业务 DTO；后续 task 把 7 个直 import generated schema
的文件全部切到此层。"
```

---

## Task 4: D1 — 全前端 7 文件 grep replace + 校验

**Files:** （一次性全切）
- Modify: `frontend/src/features/types/form/type-form.tsx`
- Modify: `frontend/src/features/assets/form/general-fields-form.tsx`
- Modify: `frontend/src/features/assets/form/asset-form-fields.tsx`
- Modify: `frontend/src/features/types/list/types-table.tsx`
- Modify: `frontend/src/features/types/list/types-page.tsx`
- Modify: `frontend/src/features/types/detail/type-summary-card.tsx`
- Modify: `frontend/src/features/types/detail/type-delete-dialog.tsx`

- [ ] **Step 4.1: 列出 7 个文件并逐一确认现状**

```bash
grep -n "from '@/api/generated/schema'" frontend/src/features/types/form/type-form.tsx
grep -n "from '@/api/generated/schema'" frontend/src/features/assets/form/general-fields-form.tsx
grep -n "from '@/api/generated/schema'" frontend/src/features/assets/form/asset-form-fields.tsx
grep -n "from '@/api/generated/schema'" frontend/src/features/types/list/types-table.tsx
grep -n "from '@/api/generated/schema'" frontend/src/features/types/list/types-page.tsx
grep -n "from '@/api/generated/schema'" frontend/src/features/types/detail/type-summary-card.tsx
grep -n "from '@/api/generated/schema'" frontend/src/features/types/detail/type-delete-dialog.tsx
```

记录每个文件的 import 行 + 它从 `components` alias 出哪些 type。

- [ ] **Step 4.2: 逐文件改 import**

每个文件做形如：

```typescript
// 原：
import type { components } from "@/api/generated/schema";
type AssetRead = components["schemas"]["AssetRead"];
type AssetTypeRead = components["schemas"]["AssetTypeRead"];

// 改：
import type { AssetRead, AssetTypeRead } from "@/features/assets/types";
```

> 局部的 inline alias（如 `type Foo = AssetRead["foo"]`）保留——`AssetRead` 类型来源换了，结构等价。

注意：`AssetTypeRead` 等 type 类型在 D1 alias 文件已 re-export，所以业务代码无须改用法。

- [ ] **Step 4.3: tsc -b 校验（关键）**

```bash
pnpm --dir frontend tsc -b
```

预期：无错。

> **重要**（来自 memory `feedback_tsc_verification.md`）：必须用 `tsc -b` 而非 `tsc --noEmit`——单 pass 会漏 7+ 真错。`pnpm build` 跑的也是 `tsc -b`。

- [ ] **Step 4.4: 跑全套前端单测**

```bash
pnpm --dir frontend test
```

预期：全 PASS（仅 import 替换，行为未变）。

- [ ] **Step 4.5: 验 grep 已干净**

```bash
grep -rn "from '@/api/generated/schema'" frontend/src 2>&1 | grep -v "frontend/src/features/assets/types.ts" | grep -v "frontend/src/api/types.ts" | wc -l
```

预期：0（除了 D1 alias 层 + H4 api/types.ts 自己）。

- [ ] **Step 4.6: 提交**

```bash
git add frontend/src/**/*.tsx frontend/src/**/*.ts
git commit -m "refactor(types): D1 全前端 grep replace 7 文件 → 业务 alias 层

types/form/type-form / assets/form/general-fields-form, asset-form-fields /
types/list/types-table, types-page / types/detail/type-summary-card,
type-delete-dialog 共 7 文件。

tsc -b 校验通过；前端单测全绿。spec §B.5 决策 C 闭环。"
```

---

## Task 5: C3 前端切 — 删 `useAssetTypesQuery()` 调用

**Files:**
- Modify: `frontend/src/features/assets/detail/asset-detail-page.tsx`
- Test: `frontend/tests/hooks/asset-detail-page.test.tsx`（如已有，补 case 验 type_name 直读）

- [ ] **Step 5.1: 看现状**

```bash
grep -n "useAssetTypesQuery\|type_name\|asset.type_name" frontend/src/features/assets/detail/asset-detail-page.tsx
```

记录 useAssetTypesQuery 调用位置 + 当前查 `type_name` 的方式。

- [ ] **Step 5.2: 改 detail page**

```typescript
// frontend/src/features/assets/detail/asset-detail-page.tsx
// 1. 删 useAssetTypesQuery 的 import 与调用
// 2. 删 types lookup（如 const typeName = types.find(...)）
// 3. 直接读 asset.type_name（PR-1 spec 已确认 AssetRead.type_name 现状已满足）

// 改前（示例）:
// const { data: asset } = useAssetQuery(id);
// const { data: types } = useAssetTypesQuery();
// const typeName = types?.find(t => t.id === asset?.type_id)?.name;
//
// 改后:
// const { data: asset } = useAssetQuery(id);
// const typeName = asset?.type_name;
```

- [ ] **Step 5.3: tsc -b**

```bash
pnpm --dir frontend tsc -b
```

预期：无错。

- [ ] **Step 5.4: 跑详情页相关测试**

```bash
pnpm --dir frontend test -- asset-detail
```

预期：全 PASS。如果 mock 中没补 `type_name`，加进 MSW handlers。

- [ ] **Step 5.5: 提交**

```bash
git add frontend/src/features/assets/detail/asset-detail-page.tsx frontend/tests
git commit -m "refactor(detail): C3 用 detail DTO 自带 type_name

删 useAssetTypesQuery 调用 + types lookup；M3a Asset.type_name @property
已让 AssetRead.type_name 直接可用。少 1 个 react-query cache 条目。"
```

---

## Task 6: design-system tokens — `--chart-1..6` + dashboard atmosphere

**Files:**
- Modify: `frontend/src/styles/globals.css`
- Modify: `design-system/asset-hub/MASTER.md`（更新色板段）
- Test: `frontend/tests/unit/dashboard/chart-token.test.ts`（type_id 哈希派色稳定性）

- [ ] **Step 6.1: 写哈希派色失败测试**

```typescript
// frontend/tests/unit/dashboard/chart-token.test.ts
import { describe, expect, it } from "vitest";
import { typeIdToChartSlot } from "@/features/dashboard/charts/chart-token";

describe("typeIdToChartSlot", () => {
  it("returns slot 1..6", () => {
    expect(typeIdToChartSlot("a-1234")).toBeGreaterThanOrEqual(1);
    expect(typeIdToChartSlot("a-1234")).toBeLessThanOrEqual(6);
  });

  it("is stable for same input", () => {
    const slot1 = typeIdToChartSlot("uuid-foo");
    const slot2 = typeIdToChartSlot("uuid-foo");
    expect(slot1).toBe(slot2);
  });

  it("returns css var name", () => {
    const v = typeIdToChartTokenVar("uuid-foo");
    expect(v).toMatch(/^var\(--chart-[1-6]\)$/);
  });
});
```

- [ ] **Step 6.2: 加 6 槽 token 到 globals.css**

```css
/* frontend/src/styles/globals.css 在现有 OKLCH token 段附近增 */
@layer base {
  :root {
    /* ...existing tokens... */

    /* M3b 看板：chart 6 槽错位 hue (240/30/145/80/280/0)
       亮度+饱和度统一确保任意 4-5 槽组合视觉重量平衡 */
    --chart-1: oklch(0.7 0.13 240);
    --chart-2: oklch(0.7 0.13 30);
    --chart-3: oklch(0.7 0.13 145);
    --chart-4: oklch(0.7 0.13 80);
    --chart-5: oklch(0.7 0.13 280);
    --chart-6: oklch(0.7 0.13 0);

    /* dashboard atmosphere */
    --dashboard-bg-radial-from: oklch(0.985 0 0 / 0.95);
    --dashboard-bg-radial-to: oklch(1 0 0);
  }

  .dark {
    --chart-1: oklch(0.62 0.13 240);
    --chart-2: oklch(0.62 0.13 30);
    --chart-3: oklch(0.62 0.13 145);
    --chart-4: oklch(0.62 0.13 80);
    --chart-5: oklch(0.62 0.13 280);
    --chart-6: oklch(0.62 0.13 0);

    --dashboard-bg-radial-from: oklch(0.18 0.005 250 / 0.95);
    --dashboard-bg-radial-to: oklch(0.13 0.005 250);
  }
}

@theme {
  /* 暴露给 Tailwind */
  --color-chart-1: var(--chart-1);
  --color-chart-2: var(--chart-2);
  --color-chart-3: var(--chart-3);
  --color-chart-4: var(--chart-4);
  --color-chart-5: var(--chart-5);
  --color-chart-6: var(--chart-6);
}
```

- [ ] **Step 6.3: 写 chart-token helper**

```typescript
// frontend/src/features/dashboard/charts/chart-token.ts
/**
 * 类型分布 6 槽 chart token 派色 helper.
 *
 * spec §B.fd5：6 槽色相错位（240/30/145/80/280/0），亮度饱和度统一.
 * spec §3.5：按 type_id 第一个字符 charCode % 6 哈希到固定槽位，
 * 同一 type 每次进看板颜色稳定.
 */

const SLOT_COUNT = 6;

export function typeIdToChartSlot(typeId: string): number {
  if (!typeId.length) return 1;
  return (typeId.charCodeAt(0) % SLOT_COUNT) + 1; // 1..6
}

export function typeIdToChartTokenVar(typeId: string): string {
  return `var(--chart-${typeIdToChartSlot(typeId)})`;
}
```

- [ ] **Step 6.4: 跑测试通过**

```bash
pnpm --dir frontend test -- chart-token
```

预期：3 PASS。

- [ ] **Step 6.5: 更新 MASTER.md 色板段**

```markdown
# design-system/asset-hub/MASTER.md 中的色板段增

## Chart 6 槽 token (M3b 看板用)

| Token | Hue | 用途 |
|---|---|---|
| `--chart-1` | 240° (蓝) | 类型分布派色槽 1 |
| `--chart-2` | 30° (橙) | 类型分布派色槽 2 |
| `--chart-3` | 145° (绿) | 类型分布派色槽 3 |
| `--chart-4` | 80° (黄) | 类型分布派色槽 4 |
| `--chart-5` | 280° (紫) | 类型分布派色槽 5 |
| `--chart-6` | 0° (红) | 类型分布派色槽 6 |

亮度/饱和度统一 `oklch(0.7 0.13 <hue>)` light / `oklch(0.62 0.13 <hue>)` dark；
6 槽相邻 hue 差 ≥ 60° 防刺眼撞色。
```

- [ ] **Step 6.6: 提交**

```bash
git add frontend/src/styles/globals.css frontend/src/features/dashboard/charts/chart-token.ts frontend/tests/unit/dashboard/chart-token.test.ts design-system/asset-hub/MASTER.md
git commit -m "feat(design-system): 加 chart 6 槽 OKLCH token + dashboard atmosphere

spec §B.fd5：6 槽色相错位 240/30/145/80/280/0，亮度饱和度统一。
chart-token.ts 提供 typeId 哈希派色 helper。
MASTER.md 色板段同步登记。"
```

---

## Task 7: shadcn chart spike + 决议

**Files:**（spike 性质）
- 临时新增 `frontend/src/features/dashboard/_spike/` 探索；决议后或保留改造、或删除回 Recharts 裸用

- [ ] **Step 7.1: 安装 shadcn chart**

```bash
pnpm --dir frontend dlx shadcn@latest add chart
```

记录命令输出——若 Tailwind v4 兼容性报错，记下错误内容。

- [ ] **Step 7.2: 生成的 chart 组件位置**

```bash
ls frontend/src/components/ui/chart*
```

预期：`chart.tsx` 或类似新文件。

- [ ] **Step 7.3: 写最小 spike 验证 v4 兼容**

```typescript
// frontend/src/features/dashboard/_spike/chart-spike.tsx
import { Bar, BarChart, XAxis, YAxis } from "recharts";
import { ChartContainer, ChartTooltip, ChartTooltipContent } from "@/components/ui/chart";

const data = [
  { name: "A", value: 30 },
  { name: "B", value: 50 },
];

export function ChartSpike() {
  return (
    <ChartContainer
      config={{ value: { label: "Value", color: "var(--chart-1)" } }}
      className="h-64"
    >
      <BarChart data={data} layout="vertical">
        <XAxis type="number" />
        <YAxis dataKey="name" type="category" />
        <ChartTooltip content={<ChartTooltipContent />} />
        <Bar dataKey="value" fill="var(--color-value)" radius={[0, 4, 4, 0]} />
      </BarChart>
    </ChartContainer>
  );
}
```

挂到一个临时 route（如 `frontend/src/routes/_spike-chart.tsx`），跑 dev server 看渲染。

```bash
pnpm --dir frontend dev &
sleep 3
# 用 playwright MCP 打开 :5173/_spike-chart 看是否渲染正确
```

- [ ] **Step 7.4: 决议**

记录决议结果到 spec §3.4 注释里：

- **A 兼容**：保留 shadcn chart wrapper（`ChartContainer` / `ChartTooltipContent`），后续 4 图都用 wrapper
- **B 不兼容**（Tailwind v4 token 不解析或样式坏）：回 Recharts 裸用——shadcn `chart.tsx` 删除，自写极薄 wrapper（参考 shadcn 源码精简）

- [ ] **Step 7.5: 删 spike 文件 + 提交**

```bash
rm -rf frontend/src/features/dashboard/_spike
rm frontend/src/routes/_spike-chart.tsx
# 如决议 B：删 frontend/src/components/ui/chart.tsx；记录决议
git add frontend/src/components/ui frontend/src/features/dashboard
git commit -m "spike(dashboard): shadcn chart Tailwind v4 兼容验证

决议：[A 保留 shadcn wrapper / B 回 Recharts 裸用 + 极薄自写 wrapper].
理由：[实测结果]."
```

---

## Task 8: dashboard 路由 + search-schema

**Files:**
- Create: `frontend/src/routes/dashboard.tsx`
- Create: `frontend/src/features/dashboard/search-schema.ts`
- Test: `frontend/tests/unit/dashboard/search-schema.test.ts`

- [ ] **Step 8.1: 写 schema 测试**

```typescript
// frontend/tests/unit/dashboard/search-schema.test.ts
import { describe, expect, it } from "vitest";
import { dashboardSearchSchema } from "@/features/dashboard/search-schema";

describe("dashboardSearchSchema", () => {
  it("defaults are false", () => {
    const result = dashboardSearchSchema.parse({});
    expect(result.include_retired).toBe(false);
    expect(result.include_disposed).toBe(false);
  });

  it("accepts URL query string booleans", () => {
    expect(dashboardSearchSchema.parse({ include_retired: true })).toMatchObject({
      include_retired: true,
    });
  });

  it("rejects invalid types", () => {
    expect(() => dashboardSearchSchema.parse({ include_retired: "yes" })).toThrow();
  });
});
```

- [ ] **Step 8.2: 写 schema**

```typescript
// frontend/src/features/dashboard/search-schema.ts
import { z } from "zod";

export const dashboardSearchSchema = z.object({
  include_retired: z.boolean().default(false),
  include_disposed: z.boolean().default(false),
});

export type DashboardSearch = z.infer<typeof dashboardSearchSchema>;
```

- [ ] **Step 8.3: 写 route 文件**

```typescript
// frontend/src/routes/dashboard.tsx
import { createFileRoute } from "@tanstack/react-router";

import { DashboardPage } from "@/features/dashboard/dashboard-page";
import { dashboardSearchSchema } from "@/features/dashboard/search-schema";

export const Route = createFileRoute("/dashboard")({
  validateSearch: dashboardSearchSchema,
  component: DashboardPage,
});
```

> Task 11 才会建 `dashboard-page.tsx`；此 task 暂建占位文件让 import 通：

```typescript
// frontend/src/features/dashboard/dashboard-page.tsx (占位)
export function DashboardPage() {
  return <div>Dashboard 占位</div>;
}
```

- [ ] **Step 8.4: tsc + 测试**

```bash
pnpm --dir frontend tsc -b
pnpm --dir frontend test -- search-schema
```

预期：tsc 无错；3 PASS。

- [ ] **Step 8.5: 提交**

```bash
git add frontend/src/routes/dashboard.tsx frontend/src/features/dashboard/search-schema.ts frontend/src/features/dashboard/dashboard-page.tsx frontend/tests/unit/dashboard/search-schema.test.ts
git commit -m "feat(dashboard): /dashboard 路由 + search-schema 骨架

include_retired/include_disposed URL 持久化；DashboardPage 占位
（Task 11 替换为完整页面）."
```

---

## Task 9: useStatsQuery + MSW + 空态判定纯函数

**Files:**
- Create: `frontend/src/features/dashboard/use-stats-query.ts`
- Create: `frontend/src/features/dashboard/empty-state.ts`（4 种空态判定）
- Modify: `frontend/tests/msw-handlers.ts`（增 stats handler）
- Test: `frontend/tests/hooks/use-stats-query.test.tsx`
- Test: `frontend/tests/unit/dashboard/empty-state.test.ts`

- [ ] **Step 9.1: 写空态判定测试**

```typescript
// frontend/tests/unit/dashboard/empty-state.test.ts
import { describe, expect, it } from "vitest";

import {
  type DashboardEmptyKind,
  detectDashboardEmpties,
} from "@/features/dashboard/empty-state";
import type { StatsRead } from "@/features/assets/types";

const fullStats: StatsRead = {
  type_distribution: [{ type_id: "x", type_name: "L", count: 5 }],
  status_distribution: { IDLE: 3 },
  holder_ranking: [{ holder: "张三", count: 5 }],
  idle_top: [{
    asset_id: "x", asset_code: "L-001", type_name: "L",
    current_location: null, idle_days: 30, idle_since: "2026-04-01T00:00:00Z",
  }],
  summary: {
    total_assets: 5, registered_assets: 5, idle_count: 3,
    include_retired: false, include_disposed: false,
    generated_at: "2026-05-06T10:00:00Z",
  },
};

describe("detectDashboardEmpties", () => {
  it("returns no empties for full stats", () => {
    expect(detectDashboardEmpties(fullStats)).toEqual([]);
  });

  it("detects type empty when type_distribution is []", () => {
    const e = detectDashboardEmpties({ ...fullStats, type_distribution: [] });
    expect(e).toContain<DashboardEmptyKind>("type");
  });

  it("detects status empty when all status counts are 0", () => {
    const e = detectDashboardEmpties({ ...fullStats, status_distribution: {} });
    expect(e).toContain<DashboardEmptyKind>("status");
  });

  it("detects holder empty when holder_ranking is []", () => {
    const e = detectDashboardEmpties({ ...fullStats, holder_ranking: [] });
    expect(e).toContain<DashboardEmptyKind>("holder");
  });

  it("detects idle empty when idle_top is []", () => {
    const e = detectDashboardEmpties({ ...fullStats, idle_top: [] });
    expect(e).toContain<DashboardEmptyKind>("idle");
  });

  it("does NOT mark short list as empty (holder 5 行不视为空态)", () => {
    const shortHolder = Array.from({ length: 5 }, (_, i) => ({
      holder: `H${i}`, count: i + 1,
    }));
    const e = detectDashboardEmpties({ ...fullStats, holder_ranking: shortHolder });
    expect(e).not.toContain<DashboardEmptyKind>("holder");
  });
});
```

- [ ] **Step 9.2: 实现空态判定**

```typescript
// frontend/src/features/dashboard/empty-state.ts
import type { StatsRead } from "@/features/assets/types";

export type DashboardEmptyKind = "type" | "status" | "holder" | "idle";

/**
 * 按 spec §3.7：每图独立判定，length === 0 才空态；
 * 短列（holder 5 行 / idle 6 行）不视为空态——"少 = 好事".
 */
export function detectDashboardEmpties(stats: StatsRead): DashboardEmptyKind[] {
  const empties: DashboardEmptyKind[] = [];

  if (stats.type_distribution !== undefined && stats.type_distribution.length === 0) {
    empties.push("type");
  }
  if (
    stats.status_distribution !== undefined &&
    Object.values(stats.status_distribution).every((c) => c === 0)
  ) {
    empties.push("status");
  }
  if (stats.holder_ranking !== undefined && stats.holder_ranking.length === 0) {
    empties.push("holder");
  }
  if (stats.idle_top !== undefined && stats.idle_top.length === 0) {
    empties.push("idle");
  }

  return empties;
}
```

- [ ] **Step 9.3: 写 useStatsQuery hook**

```typescript
// frontend/src/features/dashboard/use-stats-query.ts
import { useQuery } from "@tanstack/react-query";

import { client } from "@/api/client";
import { unwrap } from "@/api/types";
import type { StatsRead } from "@/features/assets/types";

interface UseStatsQueryParams {
  includeRetired: boolean;
  includeDisposed: boolean;
}

export function useStatsQuery({ includeRetired, includeDisposed }: UseStatsQueryParams) {
  return useQuery<StatsRead>({
    queryKey: ["stats", { includeRetired, includeDisposed }],
    queryFn: () =>
      client
        .GET("/api/stats", {
          params: {
            query: {
              include_retired: includeRetired,
              include_disposed: includeDisposed,
            },
          },
        })
        .then(unwrap),
    staleTime: 30_000,
  });
}
```

- [ ] **Step 9.4: 加 MSW handler**

```typescript
// frontend/tests/msw-handlers.ts 增量
import { http, HttpResponse } from "msw";

export const statsHandlers = [
  http.get("/api/stats", ({ request }) => {
    const url = new URL(request.url);
    const includeRetired = url.searchParams.get("include_retired") === "true";
    const includeDisposed = url.searchParams.get("include_disposed") === "true";
    const status: Record<string, number> = { IDLE: 78, IN_USE: 92, MAINTENANCE: 12 };
    if (includeRetired) status.RETIRED = 4;
    if (includeDisposed) status.DISPOSED = 1;
    return HttpResponse.json({
      type_distribution: [
        { type_id: "uuid-1", type_name: "Laptop", count: 71 },
      ],
      status_distribution: status,
      holder_ranking: [{ holder: "张三", count: 28 }],
      idle_top: [],
      summary: {
        total_assets: 187,
        registered_assets: 182,
        idle_count: 78,
        include_retired: includeRetired,
        include_disposed: includeDisposed,
        generated_at: new Date().toISOString(),
      },
    });
  }),
];
```

加进现有 handlers 数组导出。

- [ ] **Step 9.5: 写 hook 测试**

```typescript
// frontend/tests/hooks/use-stats-query.test.tsx
import { renderHook, waitFor } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { useStatsQuery } from "@/features/dashboard/use-stats-query";
import { createWrapper } from "../msw-test-wrapper"; // 参考项目现有 hook 测试 wrapper

describe("useStatsQuery", () => {
  it("fetches stats with toggle params", async () => {
    const { result } = renderHook(
      () => useStatsQuery({ includeRetired: false, includeDisposed: false }),
      { wrapper: createWrapper() }
    );
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.summary.include_retired).toBe(false);
    expect(result.current.data?.status_distribution).not.toHaveProperty("RETIRED");
  });

  it("toggle include_retired triggers refetch with new param", async () => {
    const { result } = renderHook(
      () => useStatsQuery({ includeRetired: true, includeDisposed: false }),
      { wrapper: createWrapper() }
    );
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.status_distribution).toHaveProperty("RETIRED");
  });
});
```

- [ ] **Step 9.6: 跑测试**

```bash
pnpm --dir frontend test -- empty-state
pnpm --dir frontend test -- use-stats-query
```

预期：6 + 2 = 8 PASS。

- [ ] **Step 9.7: 提交**

```bash
git add frontend/src/features/dashboard/use-stats-query.ts frontend/src/features/dashboard/empty-state.ts frontend/tests/msw-handlers.ts frontend/tests/hooks/use-stats-query.test.tsx frontend/tests/unit/dashboard/empty-state.test.ts
git commit -m "feat(dashboard): useStatsQuery + 4 种空态判定纯函数

useQuery staleTime 30s；URL toggle 反映在 queryKey 触发 refetch。
detectDashboardEmpties() 按 spec §3.7 4 种空态独立判定，
length === 0 才空态；短列不视为空态（'少 = 好事'）."
```

---

## Task 10: 看板顶栏（h1 + 副标 + inline pill toggle）

**Files:**
- Create: `frontend/src/features/dashboard/dashboard-header.tsx`
- Test: `frontend/tests/components/dashboard-header.test.tsx`

- [ ] **Step 10.1: 写测试**

```typescript
// frontend/tests/components/dashboard-header.test.tsx
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { DashboardHeader } from "@/features/dashboard/dashboard-header";

describe("DashboardHeader", () => {
  it("renders h1 + subtitle", () => {
    render(<DashboardHeader includeRetired={false} includeDisposed={false} onToggle={vi.fn()} />);
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent("看板");
    expect(screen.getByText(/实时盘点/)).toBeInTheDocument();
  });

  it("toggle pills reflect prop state", () => {
    render(<DashboardHeader includeRetired={true} includeDisposed={false} onToggle={vi.fn()} />);
    expect(screen.getByRole("button", { name: /已退役/ })).toHaveAttribute("data-state", "on");
    expect(screen.getByRole("button", { name: /已处置/ })).toHaveAttribute("data-state", "off");
  });

  it("clicking pill calls onToggle with toggled state", () => {
    const onToggle = vi.fn();
    render(<DashboardHeader includeRetired={false} includeDisposed={false} onToggle={onToggle} />);
    fireEvent.click(screen.getByRole("button", { name: /已退役/ }));
    expect(onToggle).toHaveBeenCalledWith({ include_retired: true, include_disposed: false });
  });

  it("hint icon renders with title attr", () => {
    render(<DashboardHeader includeRetired={false} includeDisposed={false} onToggle={vi.fn()} />);
    expect(screen.getByTitle(/默认排除/)).toBeInTheDocument();
  });
});
```

- [ ] **Step 10.2: 实现 header**

```tsx
// frontend/src/features/dashboard/dashboard-header.tsx
import { HelpCircle } from "lucide-react";

import { cn } from "@/lib/utils";
import type { DashboardSearch } from "./search-schema";

interface Props {
  includeRetired: boolean;
  includeDisposed: boolean;
  onToggle: (next: DashboardSearch) => void;
}

export function DashboardHeader({ includeRetired, includeDisposed, onToggle }: Props) {
  return (
    <div className="flex items-baseline justify-between mb-8">
      <div className="flex flex-col gap-1">
        <h1 className="text-3xl font-display font-medium tracking-tight">看板</h1>
        <p className="text-sm text-muted-foreground">实时盘点 + 闲置督促</p>
      </div>

      <div className="flex items-center gap-3">
        <TogglePill
          label="已退役"
          tokenClass="data-[state=on]:bg-status-retired/15 data-[state=on]:text-status-retired"
          state={includeRetired ? "on" : "off"}
          onClick={() => onToggle({
            include_retired: !includeRetired,
            include_disposed: includeDisposed,
          })}
        />
        <TogglePill
          label="已处置"
          tokenClass="data-[state=on]:bg-status-disposed/15 data-[state=on]:text-status-disposed"
          state={includeDisposed ? "on" : "off"}
          onClick={() => onToggle({
            include_retired: includeRetired,
            include_disposed: !includeDisposed,
          })}
        />
        <HelpCircle
          className="size-3.5 text-muted-foreground/60"
          aria-label="提示"
          // hover tooltip; jsdom 不支持 :hover，用 title attr 让测试可断言
        >
          <title>默认排除已退役/已处置（与列表一致）</title>
        </HelpCircle>
      </div>
    </div>
  );
}

interface TogglePillProps {
  label: string;
  tokenClass: string;
  state: "on" | "off";
  onClick: () => void;
}

function TogglePill({ label, tokenClass, state, onClick }: TogglePillProps) {
  return (
    <button
      type="button"
      role="button"
      data-state={state}
      onClick={onClick}
      aria-label={label}
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium",
        "border-border/60 text-muted-foreground transition-colors",
        "hover:bg-muted",
        tokenClass,
      )}
    >
      <span
        className={cn(
          "size-1.5 rounded-full transition-colors",
          state === "on" ? "bg-current" : "bg-muted-foreground/40"
        )}
      />
      {label}
    </button>
  );
}
```

- [ ] **Step 10.3: 跑测试**

```bash
pnpm --dir frontend test -- dashboard-header
```

预期：4 PASS。

- [ ] **Step 10.4: 提交**

```bash
git add frontend/src/features/dashboard/dashboard-header.tsx frontend/tests/components/dashboard-header.test.tsx
git commit -m "feat(dashboard): 顶栏 h1 + 副标 + inline pill toggle (基线对齐)

spec §B.fd3：拒绝 '右上角 standalone toggle button' SaaS 模板；
inline pill 形态 + dot 前缀指示 on/off + status token 弱化版 active 态。
hint icon 含 title attr 解释默认排除语义。"
```

---

## Task 11: dashboard-page D-原版 grid + atmosphere

**Files:**
- Modify: `frontend/src/features/dashboard/dashboard-page.tsx`（替换占位）

- [ ] **Step 11.1: 写完整页面（图组件先 stub）**

```tsx
// frontend/src/features/dashboard/dashboard-page.tsx
import { Route as DashboardRoute } from "@/routes/dashboard";

import { DashboardHeader } from "./dashboard-header";
import { useStatsQuery } from "./use-stats-query";
// Task 12-14 各图组件（先 stub 占位）：
import { IdleTopBarChart } from "./charts/idle-top-bar-chart";
import { TypeDistributionChart } from "./charts/type-distribution-chart";
import { StatusDistributionChart } from "./charts/status-distribution-chart";
import { HolderLeaderboard } from "./charts/holder-leaderboard";
import { DashboardSkeleton } from "./skeleton";
import { DashboardErrorBanner } from "./error-banner";

export function DashboardPage() {
  const search = DashboardRoute.useSearch();
  const navigate = DashboardRoute.useNavigate();
  const { data: stats, isLoading, error, refetch } = useStatsQuery({
    includeRetired: search.include_retired,
    includeDisposed: search.include_disposed,
  });

  return (
    <main
      className="relative min-h-[calc(100vh-4rem)] px-6 py-8"
      style={{
        backgroundImage:
          "radial-gradient(circle at 50% 20%, var(--dashboard-bg-radial-from), var(--dashboard-bg-radial-to))",
      }}
    >
      <div className="border-b border-border/40 mb-8" /> {/* hairline */}

      <DashboardHeader
        includeRetired={search.include_retired}
        includeDisposed={search.include_disposed}
        onToggle={(next) => navigate({ search: () => next })}
      />

      {isLoading ? (
        <DashboardSkeleton />
      ) : error ? (
        <DashboardErrorBanner onRetry={() => refetch()} />
      ) : stats ? (
        <div className="grid grid-cols-1 lg:grid-cols-[3fr_2fr] gap-6 min-h-[640px]">
          <IdleTopBarChart data={stats.idle_top ?? []} />
          <div className="grid grid-rows-3 gap-6">
            <TypeDistributionChart data={stats.type_distribution ?? []} />
            <StatusDistributionChart data={stats.status_distribution ?? {}} />
            <HolderLeaderboard data={stats.holder_ranking ?? []} />
          </div>
        </div>
      ) : null}
    </main>
  );
}
```

- [ ] **Step 11.2: 建图组件 stub**

```tsx
// frontend/src/features/dashboard/charts/idle-top-bar-chart.tsx (stub)
import type { IdleTopItem } from "@/features/assets/types";
export function IdleTopBarChart({ data }: { data: IdleTopItem[] }) {
  return <div className="rounded-lg border bg-card p-6">闲置 Top 10 占位 ({data.length})</div>;
}
```

3 个其他图组件同样 stub（5-6 行各）。

- [ ] **Step 11.3: 建 Skeleton + ErrorBanner stub**

```tsx
// frontend/src/features/dashboard/skeleton.tsx (stub)
export function DashboardSkeleton() {
  return <div>Skeleton 占位</div>;
}

// frontend/src/features/dashboard/error-banner.tsx (stub)
export function DashboardErrorBanner({ onRetry }: { onRetry: () => void }) {
  return (
    <div role="alert" className="rounded-md border border-destructive/40 bg-destructive/10 p-4">
      <p>看板加载失败</p>
      <button onClick={onRetry} className="mt-2 text-sm underline">重试</button>
    </div>
  );
}
```

- [ ] **Step 11.4: tsc + 跑测试**

```bash
pnpm --dir frontend tsc -b
pnpm --dir frontend test
```

预期：tsc 无错；测试全 PASS。

- [ ] **Step 11.5: 提交**

```bash
git add frontend/src/features/dashboard
git commit -m "feat(dashboard): D-原版 grid 容器 + radial atmosphere

spec §3.2：grid-cols-[3fr_2fr] gap-6 min-h-[640px]；
radial gradient 顶部 hairline border 替代 solid 背景；
4 图组件 + Skeleton + ErrorBanner stub 占位（后续 task 替换）."
```

---

## Task 12: IdleTopBarChart + TypeDistributionChart

**Files:**
- Modify: `frontend/src/features/dashboard/charts/idle-top-bar-chart.tsx`
- Modify: `frontend/src/features/dashboard/charts/type-distribution-chart.tsx`
- Test: `frontend/tests/components/idle-top-bar-chart.test.tsx`
- Test: `frontend/tests/components/type-distribution-chart.test.tsx`

- [ ] **Step 12.1: 写 idle-top Recharts BarChart**

按 spec §3.3 严格用 Recharts `BarChart layout="vertical"`——保留闲置榜 = chart shape / 保管人 = list shape 的 4 种 shape 强约束（决策 §B.1 第 3 条）。type_name + location 走 tooltip，不挤 bar 旁。

```tsx
// frontend/src/features/dashboard/charts/idle-top-bar-chart.tsx
import {
  Bar, BarChart, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import { Clock } from "lucide-react";

import type { IdleTopItem } from "@/features/assets/types";

import { IdleEmpty } from "../empty-states/idle-empty";

const IDLE_THRESHOLD_DAYS = 90;
const ANIMATION_MS = 480;

interface Props {
  data: IdleTopItem[];
}

export function IdleTopBarChart({ data }: Props) {
  if (data.length === 0) return <IdleEmpty />;

  // Recharts vertical layout：YAxis = category (asset_code), XAxis = value (idle_days)
  return (
    <section className="rounded-lg border bg-card p-6 flex flex-col">
      <header className="mb-4 flex items-baseline justify-between">
        <h2 className="text-base font-medium">闲置时长 Top 10</h2>
        <span className="text-xs text-muted-foreground">超 90 天可考虑退役 / 重派发</span>
      </header>
      <div className="flex-1 min-h-0">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={data}
            layout="vertical"
            margin={{ top: 8, right: 60, bottom: 8, left: 8 }}
          >
            {/* spec §3.4 override：CartesianGrid 隐藏（默认就不渲染 since 不引入）*/}
            <XAxis
              type="number"
              tickLine={false}
              axisLine={false}
              tick={{ fill: "var(--muted-foreground)", fontSize: 11 }}
              tickFormatter={(v) => `${v}d`}
            />
            <YAxis
              type="category"
              dataKey="asset_code"
              tickLine={false}
              axisLine={false}
              tick={{ fill: "var(--foreground)", fontSize: 11 }}
              width={90}
            />
            <Tooltip
              cursor={{ fill: "var(--muted)", opacity: 0.4 }}
              content={<IdleTooltip />}
            />
            <Bar
              dataKey="idle_days"
              radius={[0, 4, 4, 0]}
              animationDuration={ANIMATION_MS}
              animationEasing="ease-out"
              isAnimationActive
            >
              {data.map((item) => (
                <Cell
                  key={item.asset_id}
                  fill={
                    item.idle_days > IDLE_THRESHOLD_DAYS
                      ? "var(--checkout-internal)"
                      : "color-mix(in oklch, var(--checkout-internal) 70%, transparent)"
                  }
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </section>
  );
}

interface TooltipPayload {
  payload: IdleTopItem;
}

function IdleTooltip({ active, payload }: { active?: boolean; payload?: TooltipPayload[] }) {
  if (!active || !payload?.length) return null;
  const item = payload[0].payload;
  const overdue = item.idle_days > IDLE_THRESHOLD_DAYS;
  return (
    <div className="rounded-md border bg-popover px-3 py-2 shadow-md text-xs space-y-1">
      <div className="font-medium">{item.asset_code}</div>
      <div className="text-muted-foreground">{item.type_name}</div>
      {item.current_location && (
        <div className="text-muted-foreground">📍 {item.current_location}</div>
      )}
      <div className={overdue ? "text-destructive font-medium flex items-center gap-1" : "tabular-nums"}>
        {overdue && <Clock className="size-3" />}
        {item.idle_days} 天闲置
      </div>
    </div>
  );
}
```

> spec §3.4 Recharts override 7 项落点：
> - CartesianGrid → 不渲染（不挂组件）✓
> - Tooltip → 自定义 `IdleTooltip`（不用 Recharts default 白底矩形）✓
> - XAxis/YAxis → `tickLine=false axisLine=false` + 自定义 tick fill/fontSize ✓
> - Bar shape → `radius={[0, 4, 4, 0]}` 端圆角 ✓
> - Bar 填色 → `<Cell>` 按 idle_days 阈值切换 `--checkout-internal` 饱和 / 透明 70% ✓
> - Animation → `animationDuration={480} animationEasing="ease-out"` ✓
> - Legend → 不渲染（单 series 无须 legend）✓

测试断言（Recharts 在 jsdom 下 SVG 渲染受限，断 section + tooltip 而非 bar 元素本身）：

```typescript
// frontend/tests/components/idle-top-bar-chart.test.tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { IdleTopBarChart } from "@/features/dashboard/charts/idle-top-bar-chart";

const item90plus = {
  asset_id: "1", asset_code: "G-001", type_name: "GPU",
  current_location: "仓库", idle_days: 152, idle_since: "2025-12-04T00:00:00Z",
};
const itemUnder90 = {
  asset_id: "2", asset_code: "L-002", type_name: "Laptop",
  current_location: null, idle_days: 30, idle_since: "2026-04-06T00:00:00Z",
};

describe("IdleTopBarChart", () => {
  it("renders empty state when data is []", () => {
    render(<IdleTopBarChart data={[]} />);
    expect(screen.getByText(/没有闲置资产/)).toBeInTheDocument();
  });

  it("renders section header when data exists", () => {
    render(<IdleTopBarChart data={[item90plus, itemUnder90]} />);
    expect(screen.getByText("闲置时长 Top 10")).toBeInTheDocument();
    expect(screen.getByText(/超 90 天可考虑退役/)).toBeInTheDocument();
  });

  it("renders Recharts container", () => {
    const { container } = render(<IdleTopBarChart data={[item90plus]} />);
    // Recharts 包装一个 .recharts-wrapper div
    expect(container.querySelector(".recharts-wrapper")).toBeInTheDocument();
  });

  // Bar 本体的 fill / radius / Cell color 走 visual snapshot (playwright MCP)
  // jsdom 下 SVG path d 等渲染细节断言不可靠，留给 Task 16 烟测
});
```

> Recharts 组件在 jsdom 下行为受限（SVG layout 计算依赖浏览器渲染）。bar 颜色 / 圆角 / animation 等 visual 细节走 Task 16 playwright MCP 烟测断言。此处单测仅断 React 树结构 + 空态 + section header。

- [ ] **Step 12.2: 写 type-distribution donut**

```tsx
// frontend/src/features/dashboard/charts/type-distribution-chart.tsx
import { Pie, PieChart, ResponsiveContainer, Cell } from "recharts";

import type { TypeDistributionItem } from "@/features/assets/types";

import { TypeEmpty } from "../empty-states/type-empty";
import { typeIdToChartTokenVar } from "./chart-token";

interface Props {
  data: TypeDistributionItem[];
}

export function TypeDistributionChart({ data }: Props) {
  if (data.length === 0) return <TypeEmpty />;

  const total = data.reduce((sum, item) => sum + item.count, 0);

  return (
    <section className="rounded-lg border bg-card p-6 flex flex-col">
      <h2 className="text-base font-medium mb-4">类型分布</h2>
      <div className="flex items-center gap-6 flex-1">
        <div className="relative size-32 shrink-0">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={data}
                dataKey="count"
                nameKey="type_name"
                innerRadius="62%"
                outerRadius="100%"
                paddingAngle={2}
                stroke="none"
              >
                {data.map((d) => (
                  <Cell key={d.type_id} fill={typeIdToChartTokenVar(d.type_id)} />
                ))}
              </Pie>
            </PieChart>
          </ResponsiveContainer>
          {/* donut 中心总数（spec §B.fd5）*/}
          <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
            <span className="text-2xl font-medium tabular-nums">{total}</span>
            <span className="text-[10px] text-muted-foreground">件</span>
          </div>
        </div>
        <ul className="flex-1 space-y-1.5 text-xs">
          {data.map((item) => (
            <li key={item.type_id} className="flex items-center gap-2">
              <span
                className="size-2 rounded-sm"
                style={{ background: typeIdToChartTokenVar(item.type_id) }}
              />
              <span className="flex-1 truncate">{item.type_name}</span>
              <span className="tabular-nums text-muted-foreground">{item.count}</span>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}
```

测试：

```typescript
// frontend/tests/components/type-distribution-chart.test.tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { TypeDistributionChart } from "@/features/dashboard/charts/type-distribution-chart";

describe("TypeDistributionChart", () => {
  it("renders empty state when data is []", () => {
    render(<TypeDistributionChart data={[]} />);
    expect(screen.getByText(/尚未定义任何类型/)).toBeInTheDocument();
  });

  it("renders donut center total", () => {
    render(<TypeDistributionChart data={[
      { type_id: "1", type_name: "Laptop", count: 71 },
      { type_id: "2", type_name: "GPU", count: 38 },
    ]} />);
    expect(screen.getByText("109")).toBeInTheDocument();
    expect(screen.getByText("件")).toBeInTheDocument();
  });

  it("renders legend rows", () => {
    render(<TypeDistributionChart data={[
      { type_id: "1", type_name: "Laptop", count: 71 },
    ]} />);
    expect(screen.getByText("Laptop")).toBeInTheDocument();
    expect(screen.getByText("71")).toBeInTheDocument();
  });
});
```

- [ ] **Step 12.3: 跑测试**

```bash
pnpm --dir frontend test -- "(idle-top|type-distribution)"
```

预期：4 + 3 = 7 PASS。

- [ ] **Step 12.4: 提交**

```bash
git add frontend/src/features/dashboard/charts/idle-top-bar-chart.tsx frontend/src/features/dashboard/charts/type-distribution-chart.tsx frontend/tests/components/idle-top-bar-chart.test.tsx frontend/tests/components/type-distribution-chart.test.tsx
git commit -m "feat(dashboard): IdleTopBarChart + TypeDistributionChart

idle bar: 自绘 horizontal bar list (leaderboard 形态 + > 90 天 fg destructive
+ Clock icon + checkout-internal 蓝 dominant)；spec §3.5 修订配色矛盾.

type donut: 中心总数大字 (spec §B.fd5 破纯空 donut)；innerRadius 62% +
2deg paddingAngle；6 槽 chart token 派色稳定."
```

---

## Task 13: StatusDistributionChart + HolderLeaderboard

**Files:**
- Modify: `frontend/src/features/dashboard/charts/status-distribution-chart.tsx`
- Modify: `frontend/src/features/dashboard/charts/holder-leaderboard.tsx`
- Test: 各 1 个 test 文件

- [ ] **Step 13.1: 写 status stacked bar**

```tsx
// frontend/src/features/dashboard/charts/status-distribution-chart.tsx
import { STATUS_LABELS, STATUS_TOKEN_BG } from "@/components/status/status-labels";

import { StatusEmpty } from "../empty-states/status-empty";

interface Props {
  data: Record<string, number>;
}

const ORDER = ["IDLE", "IN_USE", "MAINTENANCE", "RETIRED", "DISPOSED"] as const;

export function StatusDistributionChart({ data }: Props) {
  const entries = ORDER
    .map((s) => ({ status: s, count: data[s] ?? 0 }))
    .filter((e) => e.count > 0);
  const total = entries.reduce((sum, e) => sum + e.count, 0);

  if (total === 0) return <StatusEmpty />;

  return (
    <section className="rounded-lg border bg-card p-6 flex flex-col">
      <h2 className="text-base font-medium mb-4">状态分布</h2>

      {/* 单条 stacked bar + segment 内联数字（spec §3.3 三层信号 ①）*/}
      <div className="flex h-9 rounded-md overflow-hidden">
        {entries.map((e) => {
          const pct = (e.count / total) * 100;
          return (
            <div
              key={e.status}
              className={`${STATUS_TOKEN_BG[e.status]} flex items-center justify-center text-xs font-medium text-white`}
              style={{ width: `${pct}%`, borderRight: "1px solid var(--background)" }}
              title={`${STATUS_LABELS[e.status]} ${e.count}`}
            >
              {pct >= 6 && <span>{e.count}</span>}
            </div>
          );
        })}
      </div>

      {/* dot legend（spec §3.3 三层信号 ②）*/}
      <ul className="flex flex-wrap gap-3 mt-3 text-xs">
        {entries.map((e) => (
          <li key={e.status} className="flex items-center gap-1.5">
            <span className={`size-2 rounded-sm ${STATUS_TOKEN_BG[e.status]}`} />
            <span className="text-muted-foreground">{STATUS_LABELS[e.status]}</span>
            <span className="tabular-nums">{e.count}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}
```

> 假设 M3a 已落 `STATUS_LABELS` + `STATUS_TOKEN_BG` 在 `frontend/src/components/status/status-labels.tsx`。如果不是，先 grep 确认它的实际导出名 + 路径，相应调整 import。

测试：

```typescript
// frontend/tests/components/status-distribution-chart.test.tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { StatusDistributionChart } from "@/features/dashboard/charts/status-distribution-chart";

describe("StatusDistributionChart", () => {
  it("empty state when all counts are 0", () => {
    render(<StatusDistributionChart data={{}} />);
    expect(screen.getByText(/还没有登记任何资产/)).toBeInTheDocument();
  });

  it("renders 3 segments for default 3-state", () => {
    render(<StatusDistributionChart data={{ IDLE: 78, IN_USE: 92, MAINTENANCE: 12 }} />);
    expect(screen.getByText("92")).toBeInTheDocument();
    expect(screen.getByText("78")).toBeInTheDocument();
    expect(screen.getByText("12")).toBeInTheDocument();
  });

  it("renders dot legend for all visible states", () => {
    render(<StatusDistributionChart data={{ IDLE: 5, IN_USE: 5 }} />);
    expect(screen.getByText("在用")).toBeInTheDocument();
    expect(screen.getByText("闲置")).toBeInTheDocument();
  });
});
```

- [ ] **Step 13.2: 写 holder leaderboard**

```tsx
// frontend/src/features/dashboard/charts/holder-leaderboard.tsx
import type { HolderRankingItem } from "@/features/assets/types";

import { HolderEmpty } from "../empty-states/holder-empty";

interface Props {
  data: HolderRankingItem[];
}

export function HolderLeaderboard({ data }: Props) {
  if (data.length === 0) return <HolderEmpty />;

  const max = data[0]?.count ?? 0;

  return (
    <section className="rounded-lg border bg-card p-6 flex flex-col">
      <h2 className="text-base font-medium mb-4">保管人持有</h2>
      <ul className="flex-1 max-h-72 overflow-y-auto space-y-2">
        {data.map((item) => (
          <li
            key={item.holder}
            className="grid grid-cols-[auto_1fr_auto_auto] items-center gap-2 py-1.5 border-b border-border/30 last:border-b-0"
          >
            <Avatar name={item.holder} />
            <span className="text-sm truncate">{item.holder}</span>
            {/* inline mini bar（spec §B.fd 决议 + §3.3 customization 红线）*/}
            <div className="w-12 h-[1.5px] bg-muted/40 rounded-full overflow-hidden">
              <div
                className="h-full bg-primary/40"
                style={{ width: `${Math.min(100, (item.count / max) * 100)}%` }}
              />
            </div>
            <span className="text-xs tabular-nums bg-muted text-muted-foreground rounded-full px-2 py-0.5 min-w-[2rem] text-center">
              {item.count}
            </span>
          </li>
        ))}
      </ul>
    </section>
  );
}

function Avatar({ name }: { name: string }) {
  const ch = name.slice(0, 1);
  return (
    <span className="size-5 rounded-full bg-muted flex items-center justify-center text-[10px] text-muted-foreground font-medium">
      {ch}
    </span>
  );
}
```

测试：

```typescript
// frontend/tests/components/holder-leaderboard.test.tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { HolderLeaderboard } from "@/features/dashboard/charts/holder-leaderboard";

describe("HolderLeaderboard", () => {
  it("empty state when data is []", () => {
    render(<HolderLeaderboard data={[]} />);
    expect(screen.getByText(/还没有派发记录/)).toBeInTheDocument();
  });

  it("renders all rows", () => {
    render(<HolderLeaderboard data={[
      { holder: "张三", count: 28 },
      { holder: "李四", count: 21 },
    ]} />);
    expect(screen.getByText("张三")).toBeInTheDocument();
    expect(screen.getByText("李四")).toBeInTheDocument();
    expect(screen.getByText("28")).toBeInTheDocument();
    expect(screen.getByText("21")).toBeInTheDocument();
  });

  it("first holder mini bar is full width", () => {
    const { container } = render(<HolderLeaderboard data={[
      { holder: "张三", count: 28 },
      { holder: "李四", count: 14 },
    ]} />);
    const bars = container.querySelectorAll('[style*="width"]');
    // 第一个 bar 100%
    expect((bars[0] as HTMLElement).style.width).toContain("100");
    // 第二个 bar 50%
    expect((bars[1] as HTMLElement).style.width).toContain("50");
  });
});
```

- [ ] **Step 13.3: 跑测试**

```bash
pnpm --dir frontend test -- "(status-distribution|holder-leaderboard)"
```

预期：3 + 3 = 6 PASS。

- [ ] **Step 13.4: 提交**

```bash
git add frontend/src/features/dashboard/charts/status-distribution-chart.tsx frontend/src/features/dashboard/charts/holder-leaderboard.tsx frontend/tests/components/status-distribution-chart.test.tsx frontend/tests/components/holder-leaderboard.test.tsx
git commit -m "feat(dashboard): StatusDistributionChart + HolderLeaderboard

status: 单条 stacked bar + segment 内联数字 + dot legend (spec §3.3 三层信号);
M3a 5 态 OKLCH token 复用; segment 间 1px hairline.

holder: 密集列表 (avatar + name + inline mini bar + count chip);
spec §B.fd visual 约束 — 禁用 horizontal bar chart, 4 种 shape 落形态分配."
```

---

## Task 14: 4 套 Skeleton + 4 个空态

**Files:**
- Modify: `frontend/src/features/dashboard/skeleton.tsx`（替换 stub）
- Create: `frontend/src/features/dashboard/empty-states/{type,status,holder,idle}-empty.tsx`

- [ ] **Step 14.1: 写 4 套 Skeleton（形态匹配）**

```tsx
// frontend/src/features/dashboard/skeleton.tsx
export function DashboardSkeleton() {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-[3fr_2fr] gap-6 min-h-[640px]">
      <IdleTopSkeleton />
      <div className="grid grid-rows-3 gap-6">
        <DonutSkeleton />
        <StatusBarSkeleton />
        <HolderListSkeleton />
      </div>
    </div>
  );
}

const IDLE_BAR_WIDTHS = [90, 82, 70, 58, 45, 32, 28, 22, 18, 12]; // %

function IdleTopSkeleton() {
  return (
    <div className="rounded-lg border bg-card p-6">
      <div className="h-4 w-32 bg-muted/40 rounded mb-6 animate-pulse" />
      <ul className="space-y-2">
        {IDLE_BAR_WIDTHS.map((w, i) => (
          <li key={i} className="grid grid-cols-[1fr_auto_auto] items-center gap-3">
            <div className="h-3 w-24 bg-muted/40 rounded animate-pulse" />
            <div className="w-32 sm:w-48 h-2 bg-muted/40 rounded-full overflow-hidden">
              <div
                className="h-full bg-muted/60 rounded-full animate-pulse"
                style={{ width: `${w}%` }}
              />
            </div>
            <div className="h-3 w-10 bg-muted/40 rounded animate-pulse" />
          </li>
        ))}
      </ul>
    </div>
  );
}

function DonutSkeleton() {
  return (
    <div className="rounded-lg border bg-card p-6 flex items-center gap-6">
      <div className="size-32 rounded-full border-[10px] border-muted/40 animate-pulse" />
      <div className="flex-1 space-y-2">
        <div className="h-3 w-3/4 bg-muted/40 rounded animate-pulse" />
        <div className="h-3 w-2/3 bg-muted/40 rounded animate-pulse" />
        <div className="h-3 w-1/2 bg-muted/40 rounded animate-pulse" />
      </div>
    </div>
  );
}

function StatusBarSkeleton() {
  return (
    <div className="rounded-lg border bg-card p-6">
      <div className="h-4 w-24 bg-muted/40 rounded mb-4 animate-pulse" />
      <div className="h-9 w-full bg-muted/40 rounded-md animate-pulse" />
      <div className="flex gap-3 mt-3">
        {[1, 2, 3, 4, 5].map((i) => (
          <div key={i} className="h-3 w-12 bg-muted/40 rounded animate-pulse" />
        ))}
      </div>
    </div>
  );
}

function HolderListSkeleton() {
  return (
    <div className="rounded-lg border bg-card p-6">
      <div className="h-4 w-28 bg-muted/40 rounded mb-4 animate-pulse" />
      <ul className="space-y-2">
        {[1, 2, 3, 4, 5].map((i) => (
          <li key={i} className="grid grid-cols-[auto_1fr_auto] items-center gap-2 py-1.5">
            <div className="size-5 rounded-full bg-muted/40 animate-pulse" />
            <div className="h-3 bg-muted/40 rounded animate-pulse" />
            <div className="h-3 w-8 bg-muted/40 rounded animate-pulse" />
          </li>
        ))}
      </ul>
    </div>
  );
}
```

- [ ] **Step 14.2: 4 个空态组件**

```tsx
// frontend/src/features/dashboard/empty-states/empty-card.tsx (共用)
import { type LucideIcon } from "lucide-react";
import { Link } from "@tanstack/react-router";

import { Button } from "@/components/ui/button";

interface Props {
  Icon: LucideIcon;
  title: string;
  subtitle: string;
  cta?: { to: string; label: string };
}

export function EmptyCard({ Icon, title, subtitle, cta }: Props) {
  return (
    <section className="rounded-lg border bg-card p-6 flex flex-col items-center justify-center gap-3 min-h-[200px] text-center">
      <div className="size-12 rounded-full bg-muted/50 ring-1 ring-border/50 flex items-center justify-center">
        <Icon className="size-[18px] text-muted-foreground" />
      </div>
      <div className="space-y-1">
        <h3 className="text-base font-medium font-display">{title}</h3>
        <p className="text-sm text-muted-foreground italic">{subtitle}</p>
      </div>
      {cta && (
        <Button asChild variant="outline" size="sm">
          <Link to={cta.to}>{cta.label}</Link>
        </Button>
      )}
    </section>
  );
}
```

```tsx
// frontend/src/features/dashboard/empty-states/type-empty.tsx
import { Boxes } from "lucide-react";
import { EmptyCard } from "./empty-card";
export const TypeEmpty = () => (
  <EmptyCard
    Icon={Boxes}
    title="尚未定义任何类型"
    subtitle="先建一个类型再开始登记"
    cta={{ to: "/types", label: "管理类型" }}
  />
);
```

```tsx
// frontend/src/features/dashboard/empty-states/status-empty.tsx
import { LayoutDashboard } from "lucide-react";
import { EmptyCard } from "./empty-card";
export const StatusEmpty = () => (
  <EmptyCard
    Icon={LayoutDashboard}
    title="还没有登记任何资产"
    subtitle="第一件资产是开始"
    cta={{ to: "/assets/new", label: "登记资产" }}
  />
);
```

```tsx
// frontend/src/features/dashboard/empty-states/holder-empty.tsx
import { UserPlus } from "lucide-react";
import { EmptyCard } from "./empty-card";
export const HolderEmpty = () => (
  <EmptyCard
    Icon={UserPlus}
    title="还没有派发记录"
    subtitle="派发出去就有人持有了"
    cta={{ to: "/assets", label: "去派发" }}
  />
);
```

```tsx
// frontend/src/features/dashboard/empty-states/idle-empty.tsx
import { Leaf } from "lucide-react";
import { EmptyCard } from "./empty-card";
export const IdleEmpty = () => (
  <EmptyCard
    Icon={Leaf}
    title="没有闲置资产"
    subtitle="一切都在用——干得不错"
    // 无 CTA — '少 = 好事'
  />
);
```

- [ ] **Step 14.3: 跑测试**

```bash
pnpm --dir frontend test -- "(idle-top|type-distribution|status-distribution|holder-leaderboard)"
pnpm --dir frontend tsc -b
```

预期：tsc 无错；前面 4 个图组件的"empty state"用例都能通（因引用了空态组件）。

- [ ] **Step 14.4: 提交**

```bash
git add frontend/src/features/dashboard/skeleton.tsx frontend/src/features/dashboard/empty-states
git commit -m "feat(dashboard): 4 套 Skeleton (形态匹配) + 4 个空态 (按图差异化)

Skeleton (spec §3.8): IdleTopSkeleton 10 行不同长度 / Donut outline + 中心
+ legend pulse / Status 1 条 bar + 5 dot / Holder 5 行 avatar+name+chip pulse.

EmptyState (spec §3.7): icon 容器 (size-12 + ring + muted bg) + display
font 标题 + italic 副标 + outline CTA; 闲置榜空态特殊 '一切都在用' 奖励文案."
```

---

## Task 15: page load Motion 编排（Framer Motion）

**Files:**
- Modify: `frontend/src/features/dashboard/dashboard-page.tsx`（包 motion）
- Test: `frontend/tests/components/dashboard-motion.test.tsx`（断言 motion 元素 data-attr）

- [ ] **Step 15.1: 装 Framer Motion**

```bash
pnpm --dir frontend add motion
```

> 项目用的是新版 `motion` 包（旧名 framer-motion）。如装失败回退 `pnpm add framer-motion`。

- [ ] **Step 15.2: 包 motion 编排**

```tsx
// frontend/src/features/dashboard/dashboard-page.tsx 修改 grid 部分
import { motion, useReducedMotion } from "motion/react";

// ...保留 isLoading / error / 顶栏部分不变...

const STAGGER = {
  idle: { delay: 0 },
  type: { delay: 0.1 },
  status: { delay: 0.18 },
  holder: { delay: 0.26 },
};

const reduceMotion = useReducedMotion();

// 替换 grid 段:
{stats ? (
  <div className="grid grid-cols-1 lg:grid-cols-[3fr_2fr] gap-6 min-h-[640px]">
    <motion.div
      initial={reduceMotion ? { opacity: 0 } : { opacity: 0, x: -8 }}
      animate={reduceMotion ? { opacity: 1 } : { opacity: 1, x: 0 }}
      transition={{
        duration: 0.32,
        ease: [0.16, 1, 0.3, 1],
        delay: STAGGER.idle.delay,
      }}
    >
      <IdleTopBarChart data={stats.idle_top ?? []} />
    </motion.div>
    <div className="grid grid-rows-3 gap-6">
      {(["type", "status", "holder"] as const).map((kind, i) => {
        const Comp = {
          type: () => <TypeDistributionChart data={stats.type_distribution ?? []} />,
          status: () => <StatusDistributionChart data={stats.status_distribution ?? {}} />,
          holder: () => <HolderLeaderboard data={stats.holder_ranking ?? []} />,
        }[kind];
        return (
          <motion.div
            key={kind}
            data-motion-kind={kind}
            initial={reduceMotion ? { opacity: 0 } : { opacity: 0, y: 8 }}
            animate={reduceMotion ? { opacity: 1 } : { opacity: 1, y: 0 }}
            transition={{
              duration: 0.32,
              ease: [0.16, 1, 0.3, 1],
              delay: STAGGER[kind].delay,
            }}
          >
            <Comp />
          </motion.div>
        );
      })}
    </div>
  </div>
) : null}
```

- [ ] **Step 15.3: 写测试**

```typescript
// frontend/tests/components/dashboard-motion.test.tsx
import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";

// motion 在 jsdom 下行为受限，这里只断 4 motion 元素都在 + data-attr 顺序
import { DashboardPage } from "@/features/dashboard/dashboard-page";
import { renderWithRouterAndQuery } from "../test-utils"; // 项目现有 wrapper

describe("DashboardPage motion", () => {
  it("renders 4 motion-wrapped sections in correct order", async () => {
    const { container } = renderWithRouterAndQuery(<DashboardPage />, {
      route: "/dashboard",
    });
    // 等待加载完成
    await new Promise((r) => setTimeout(r, 50));
    const motionKinds = Array.from(
      container.querySelectorAll("[data-motion-kind]")
    ).map((el) => el.getAttribute("data-motion-kind"));
    expect(motionKinds).toEqual(["type", "status", "holder"]);
    // 闲置锚没有 data-motion-kind（用 motion.div 但无 attr），通过其他方式断；
    // 验证至少 motion children 数符合预期
  });
});
```

- [ ] **Step 15.4: tsc + 测试**

```bash
pnpm --dir frontend tsc -b
pnpm --dir frontend test -- dashboard-motion
```

预期：通过。

- [ ] **Step 15.5: 提交**

```bash
git add frontend/package.json frontend/pnpm-lock.yaml frontend/src/features/dashboard/dashboard-page.tsx frontend/tests/components/dashboard-motion.test.tsx
git commit -m "feat(dashboard): page load staggered reveal motion

spec §3.2 + §B.fd2: 闲置锚先入场 (translateX) + 右三段 80ms 错位 (translateY).
duration 320ms / cubic-bezier(0.16, 1, 0.3, 1).
prefers-reduced-motion 退化为纯 opacity 不 translate."
```

---

## Task 16: 入口接入 + Playwright MCP 烟测 + PR-2 验收

**Files:**
- Modify: `frontend/src/components/layout/app-header.tsx`（或同等顶部导航文件）—— 加 `/dashboard` 链接
- Verify: dev server `:5173` 可访问 `/dashboard`

- [ ] **Step 16.1: 加 /dashboard 入口**

```bash
# 找当前 header 文件
grep -rn "Link.*to=.*assets\|Link.*to=.*types" frontend/src/components/layout 2>&1 | head -5
```

定位 nav 链接段，按现有模式增 `/dashboard` 链接：

```tsx
// frontend/src/components/layout/app-header.tsx
import { LayoutDashboard } from "lucide-react";

// 在现有 nav <Link> 列表中加（位置在 Assets 链接之前或之后）：
<Link to="/dashboard" className="...">
  <LayoutDashboard className="size-4" />
  <span>看板</span>
</Link>
```

- [ ] **Step 16.2: tsc 校验 + 跑全套测试**

```bash
pnpm --dir frontend tsc -b
pnpm --dir frontend test
```

预期：tsc clean；全套 vitest PASS。

- [ ] **Step 16.3: 启动 dev server**

```bash
uv run asset-hub serve start --mode dev
sleep 3
curl -s http://localhost:5173 -o /dev/null -w "%{http_code}\n"  # 应 200
```

- [ ] **Step 16.4: Playwright MCP 烟测脚本**

按 spec §6.1 烟测场景：

| 场景 | playwright MCP 调用 |
|---|---|
| 1. 看板首页 4 图同框（D-原版） | `browser_navigate(/dashboard)` + `browser_snapshot()` + 断 4 sections 都渲染 |
| 2. toggle "已退役" 联动 | `browser_click(已退役 pill)` + `browser_wait_for("RETIRED")` + `browser_snapshot()` |
| 3. toggle "已处置" 联动 | `browser_click(已处置 pill)` + 同上 |
| 4. 4 个空态（mock 数据） | 临时清空 db / 用 MSW dev mode → 各空态 snapshot |
| 5. 窄屏退化 < 1024 | `browser_resize(800, 900)` + `browser_snapshot()` |
| 6. 暗色模式 | 切 theme（theme-toggle）+ `browser_snapshot()` |
| 7. 加载 Skeleton | 慢网络模拟 / 短时间内 snapshot |

每个场景 `browser_take_screenshot()` 留视觉对比基线（不进 CI，作记录）。

写一个 markdown checklist 在 PR-2 验收 commit 中跑：

```markdown
- [ ] 4 图同框 D-原版布局 ✓
- [ ] toggle 联动 RETIRED 出现 ✓
- [ ] toggle 联动 DISPOSED 出现 ✓
- [ ] 类型空态 (mock empty types_distribution) ✓
- [ ] 状态空态 (mock empty status_distribution) ✓
- [ ] 保管人空态 (mock empty holder_ranking) ✓
- [ ] 闲置榜空态 (mock empty idle_top + 显示 '一切都在用') ✓
- [ ] 窄屏 800px 单列堆叠顺序：闲置 → 类型 → 状态 → 保管人 ✓
- [ ] 暗色模式 5 态 token 切换 ✓
- [ ] 加载 4 套 Skeleton 形态正确（10 行 idle / donut outline / status bar / holder list）✓
- [ ] page load motion 闲置锚先入 + 右三段错位（视觉验，看截图）✓
```

- [ ] **Step 16.5: 修任何视觉烟测发现的问题**

如发现：
- 配色与 spec §3.5 偏差 → 改 globals.css 或组件
- 布局错位（如某图过窄） → 微调 grid / min-h
- Skeleton 形态不匹配 → 改 Step 14.1
- motion 不流畅 / 顺序错 → 改 Step 15.2

每个修订单独 commit。

- [ ] **Step 16.6: 跑后端 + 前端最终全套测试**

```bash
uv run pytest
pnpm --dir frontend test
pnpm --dir frontend tsc -b
uv run ruff check .
```

预期：全 PASS / 无 issue。

- [ ] **Step 16.7: 验入口**

```bash
# 浏览器手动 / playwright MCP 验：
# 1. /assets 列表页顶部 nav 有 "看板" 链接
# 2. 点击 → /dashboard
# 3. /dashboard 页 nav 高亮
```

- [ ] **Step 16.8: 提交并准备 PR**

```bash
git add frontend/src/components/layout
git commit -m "feat(nav): 顶部 nav 加 /dashboard 入口"

git log --oneline main..HEAD
```

确认 PR-2 commit 顺序合规（基建 → D1 → H4 → C3 → 看板组件 → motion → 入口 → 烟测）。

PR 描述：

```
M3b PR-2：前端 /dashboard 集成 + D1/H4/C3 闭环

主线：
- /dashboard 路由 + D-原版布局（左 60% 闲置榜 / 右 40% 三段）
- 4 图：IdleTopBarChart (leaderboard 自绘) / TypeDistributionChart (donut + 中心数)
  / StatusDistributionChart (单条 stacked bar + 三层信号) / HolderLeaderboard
  (密集列表 + inline mini bar)
- 4 套 Skeleton (形态匹配最终图形)
- 4 个差异化空态 (按图独立 icon + CTA)
- page load staggered reveal motion (闲置锚先入 + 右三段 80ms 错位)
- 顶部 nav /dashboard 入口

Follow-up 闭环:
- D1: 全前端 7 文件 generated import → features/assets/types.ts 业务 alias
- H4: api/types.ts 抽 OpenapiFetchResult<T> + 简化 unwrap 签名
- C3 前端切: asset-detail-page 删 useAssetTypesQuery, 直读 asset.type_name

测试: vitest 单元 + hooks + components 全 PASS; Playwright MCP 烟测覆盖
4 空态 + 4 图同框 + toggle 联动 + 窄屏退化 + 暗色模式 + 加载.

Spec: docs/superpowers/specs/2026-05-06-m3b-dashboard-stats-design.md
```

---

## Self-Review Checklist

实施期完成 16 task 后跑：

- [ ] spec §1.1 包含项 9 条全有对应 task（前端 6 条 + follow-up 3 条）
- [ ] §3.1 路由 / §3.2 布局 / §3.3 4 图 / §3.4 图表栈 spike / §3.5 配色 / §3.6 hook / §3.7 4 空态 / §3.8 Skeleton 全部落地
- [ ] §3.4 Recharts 默认 override 7 项清单：CartesianGrid（不用，自绘 list）/ Tooltip（暂未实现，跟踪）/ Axis（自绘）/ Bar shape（自绘）/ Pie 填色（typeIdToChartTokenVar）/ Legend（自绘）/ Animation（Framer Motion 编排 + bar transition[width]）—— **审查项**：tooltip 是否已落 `<ChartTooltipContent>` 还是自写？如未落，加补
- [ ] §8 决策追踪 11 项中前端涉及（B.1-B.10 + B.fd1-fd6 + B.an4 D1 / B.an6 list 三参数 frontend search-schema 不涉及 list）全部体现在代码里
- [ ] 无 TBD/TODO/placeholder
- [ ] PR commit 顺序合规：基建 → 重构 → 看板组件 → motion → 入口 → 烟测
- [ ] motion `prefers-reduced-motion` 退化已落
- [ ] D1 grep 干净（除 alias 层与 H4 自身）

PR-2 合并即 M3b 完结，进入 M3c（导出）。
