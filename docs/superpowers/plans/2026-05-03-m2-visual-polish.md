# M2 视觉收尾 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 frontend-design 审计发现的 H 类 5 项偏差 + M2 SectionHeading 抽象一次性闭环；其余 M1/M3/M4 登记到 simplify-followups §7 留给 M3。

**Architecture:** 单 PR 多 commit，按依赖顺序 9 个任务推进（先文档/token 修订 → 公共组件 → 调用点替换 → 文档登记 → 最终验证）。所有改动局限于 `frontend/src/`、`docs/superpowers/`、`design-system/asset-hub/MASTER.md`，不触后端、不动数据库、不改 OpenAPI schema。

**Tech Stack:** React 19 / TanStack Router / shadcn/ui / Tailwind v4 (`@theme inline`) / vitest / RHF + Zod。

**Spec：** [`docs/superpowers/specs/2026-05-03-m2-visual-polish-design.md`](../specs/2026-05-03-m2-visual-polish-design.md)

---

## 文件结构

**新增**：

- `frontend/src/components/ui/section-heading.tsx` — 双导出 `<SectionTitle>` + `<SectionCaption>`
- `frontend/src/components/feedback/not-found-panel.tsx` — 公共 NotFoundPanel（`backLink` slot 形态）
- `frontend/src/features/assets/detail/asset-not-found.tsx` — 资产端 thin wrapper
- `frontend/src/features/types/detail/type-not-found.tsx` — 类型端 thin wrapper

**删除**：

- `frontend/src/features/assets/detail/not-found-panel.tsx` — asset-private 版本，被 `asset-not-found.tsx` 取代

**修改**：

- `frontend/src/styles/globals.css` — 删 `--font-heading` token
- `frontend/src/features/assets/detail/checkout-timeline.tsx` — 状态色改 token
- `frontend/src/features/assets/detail/asset-detail-page.tsx` — import + 调用点改名
- `frontend/src/features/assets/form/asset-form-fields.tsx` — caption 替换
- `frontend/src/features/assets/form/custom-fields-form.tsx` — caption 替换
- `frontend/src/features/types/list/types-page.tsx` — 接 EmptyState
- `frontend/src/features/types/list/types-table.tsx` — 表头中文化
- `frontend/src/features/types/form/type-form.tsx` — FormLabels 中文化 + 2 处 caption 替换
- `frontend/src/features/types/detail/type-detail-page.tsx` — 内联 404 改用 wrapper + caption 替换
- `frontend/src/features/types/detail/type-summary-card.tsx` — `<dt>` 中文化
- `frontend/src/routes/assets.$id.tsx` — `errorComponent` 改名
- `docs/superpowers/specs/2026-04-24-m2c1-frontend-foundation-and-list-design.md` — §3.5.3 修订
- `design-system/asset-hub/MASTER.md` — §Typography + 实施期纠偏新增节
- `docs/superpowers/simplify-followups.md` — 新增 §7
- `docs/superpowers/followup-allocation.md` — §M3 强搭车表加一行

---

### Task 1：H1 字体决议（删 token + spec/MASTER 文档）

**Files:**
- Modify: `frontend/src/styles/globals.css:11-13`
- Modify: `docs/superpowers/specs/2026-04-24-m2c1-frontend-foundation-and-list-design.md:98`
- Modify: `design-system/asset-hub/MASTER.md:31-34`（§Typography）

- [ ] **Step 1: 删 globals.css `--font-heading` token**

```diff
   --font-sans: "Fira Sans", "PingFang SC", "Microsoft YaHei UI", sans-serif;
-  --font-heading: "Fira Sans", "PingFang SC", "Microsoft YaHei UI", sans-serif;
   --font-mono: "Fira Code", ui-monospace, monospace;
```

- [ ] **Step 2: 修订 m2c1 spec §3.5.3 字体合规表 (行 98)**

把这一行：

```markdown
| Heading 字体 | Fira Code（Variable 优先） | 标题、`asset_code` 等编号字段 |
```

改成（写两行，把 mono 字段单独列出）：

```markdown
| Heading 字体 | Fira Sans（与 Body 同字型） | 标题层级靠字号区分；M2 视觉收尾决议 ([2026-05-03 spec](../specs/2026-05-03-m2-visual-polish-design.md)) |
| Mono 字段 | Fira Code | `asset_code` / `serial_number` / `code_prefix` / 时间戳 / 显式 `.font-code` 标记位置 |
```

- [ ] **Step 3: 修订 MASTER.md §Typography**

```diff
- - **Heading Font:** Fira Code
- - **Body Font:** Fira Sans
+ - **Heading Font:** Fira Sans（M2 视觉收尾纠偏，2026-05-03；原承诺 Fira Code，但 Fira Code 不渲染中文，全 fallback 到 PingFang，差异化无效；mono 字段保留 Fira Code）
+ - **Body Font:** Fira Sans
+ - **Mono Font:** Fira Code（asset_code / SN / code_prefix / 时间戳 / `.font-code`）
```

- [ ] **Step 4: 验证类型检查 + lint + 测试不受影响**

Run: `pnpm --dir frontend exec tsc -b`
Expected: 0 errors
Run: `pnpm --dir frontend lint`
Expected: 0 errors
Run: `pnpm --dir frontend test --run`
Expected: 73 passed (sumarry)

- [ ] **Step 5: Commit**

```bash
git add frontend/src/styles/globals.css \
  docs/superpowers/specs/2026-04-24-m2c1-frontend-foundation-and-list-design.md \
  design-system/asset-hub/MASTER.md
git commit -m "refactor(theme): 删 --font-heading token + 修订 spec/MASTER heading 字体承诺（H1）

放弃全站 heading 字体差异化（Fira Sans 与 Fira Code 在中文 UI 下视觉不可分辨）。
Fira Code 保留用途：mono 字段（asset_code / SN / code_prefix / 时间戳 / .font-code）。"
```

---

### Task 2：H4 TypesPage 接 EmptyState

**Files:**
- Modify: `frontend/src/features/types/list/types-page.tsx:1-58`

- [ ] **Step 1: 替换内联空态块 + 删 unused import**

整个文件替换为：

```tsx
import { useState } from 'react';
import { Link } from '@tanstack/react-router';
import { Plus } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { EmptyState } from '@/components/feedback/empty-state';
import { ErrorState } from '@/components/feedback/error-state';
import { useAssetTypesQuery } from '@/api/hooks/types';
import { TypesTable } from './types-table';
import { TypesTableSkeleton } from './types-table-skeleton';
import { TypeDeleteDialog } from '../detail/type-delete-dialog';
import type { components } from '@/api/generated/schema';

type TypeRead = components['schemas']['TypeRead'];

export function TypesPage() {
  const q = useAssetTypesQuery();
  const [deletingType, setDeletingType] = useState<TypeRead | null>(null);

  return (
    <div className="space-y-6">
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-xl font-semibold">类型管理</h1>
          {q.data && (
            <p className="text-sm text-muted-foreground">共 {q.data.length} 个类型</p>
          )}
        </div>
        <Button asChild>
          <Link to="/types/new">
            <Plus className="h-4 w-4 mr-2" />
            新建类型
          </Link>
        </Button>
      </div>

      {q.isLoading && <TypesTableSkeleton />}
      {q.isError && <ErrorState error={q.error} onRetry={() => q.refetch()} />}
      {q.data && q.data.length === 0 && (
        <EmptyState
          title="还没有类型"
          description="先创建一个类型，再为该类型登记资产"
          action={
            <Button asChild>
              <Link to="/types/new">创建第一个类型</Link>
            </Button>
          }
        />
      )}
      {q.data && q.data.length > 0 && (
        <TypesTable rows={q.data} onDelete={setDeletingType} />
      )}

      {deletingType && (
        <TypeDeleteDialog
          type={deletingType}
          onClose={() => setDeletingType(null)}
        />
      )}
    </div>
  );
}
```

变更要点：
- 删除 `Inbox` 的 import（已被 EmptyState 内部使用）
- 新增 `EmptyState` 的 import
- 空态块改用 `<EmptyState>`，文案 "还没有类型" + description "先创建一个类型，再为该类型登记资产"

- [ ] **Step 2: 验证类型检查**

Run: `pnpm --dir frontend exec tsc -b`
Expected: 0 errors

- [ ] **Step 3: 验证测试不受影响**

Run: `pnpm --dir frontend test --run`
Expected: 73 passed

- [ ] **Step 4: 验证 lint**

Run: `pnpm --dir frontend lint`
Expected: 0 errors（特别确认 unused import `Inbox` 已删）

- [ ] **Step 5: Commit**

```bash
git add frontend/src/features/types/list/types-page.tsx
git commit -m "refactor(types-list): 空态接入公共 EmptyState 组件（H4 / simplify §T）"
```

---

### Task 3：H3 timeline 状态色改 token

**Files:**
- Modify: `frontend/src/features/assets/detail/checkout-timeline.tsx:55-59`

- [ ] **Step 1: 替换 hex fallback 为 status-in-use token**

`checkout-timeline.tsx:55-59` 当前：

```tsx
{ongoing && (
  <span className="shrink-0 rounded-sm bg-[var(--status-active,#16a34a)]/10 px-2 py-0.5 text-xs font-medium text-[var(--status-active,#16a34a)]">
    派发中
  </span>
)}
```

改为：

```tsx
{ongoing && (
  <span className="shrink-0 rounded-sm bg-status-in-use px-2 py-0.5 text-xs font-medium text-status-in-use-fg">
    派发中
  </span>
)}
```

注：原 `bg-...active...)/10` 透明度暗示色块淡。`--status-in-use` 已是 OKLCH 浅绿（`oklch(0.92 0.08 155)`），不再需要 `/10` 调淡。

- [ ] **Step 2: 验证类型检查 + lint**

Run: `pnpm --dir frontend exec tsc -b`
Expected: 0 errors
Run: `pnpm --dir frontend lint`
Expected: 0 errors

- [ ] **Step 3: 启动 dev server 浅/深模式手工烟测**

Run: `pnpm --dir frontend dev`（或 `uv run asset-hub serve start --mode dev`）
打开浏览器：`http://localhost:5173`
导航到任一 IN_USE 资产的详情页，下拉到"流转记录" section
- 浅色模式："派发中" pill 显示柔和浅绿背景 + 深绿文字（match StatusBadge "在用" 视觉）
- 切深色模式：pill 显示暗绿背景 + 亮绿文字
- 不再出现 emerald-600 那种饱和度很高的绿色

- [ ] **Step 4: Commit**

```bash
git add frontend/src/features/assets/detail/checkout-timeline.tsx
git commit -m "fix(timeline): \"派发中\" pill 改用 status-in-use token 替换 hex fallback（H3）

原 bg-[var(--status-active,#16a34a)]/10 中 --status-active 从未定义，
每次回落到 hex emerald-600，绕开 OKLCH dark-mode 独立调机制。"
```

---

### Task 4：建 SectionHeading 双组件（不替换调用点）

**Files:**
- Create: `frontend/src/components/ui/section-heading.tsx`

- [ ] **Step 1: 创建 section-heading.tsx**

```tsx
import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

interface Props {
  children: ReactNode;
  className?: string;
}

/** 详情阅读区 section 标题（GeneralFields / AttachmentGrid / CheckoutTimeline 风格）。 */
export function SectionTitle({ children, className }: Props) {
  return (
    <h2 className={cn("mb-3 text-lg font-medium", className)}>{children}</h2>
  );
}

/** 表单 / 元信息密度区 section caption。
 *  CJK 字符上 `text-transform: uppercase` 无效，留给英文场景生效；中文渲染不变。 */
export function SectionCaption({ children, className }: Props) {
  return (
    <h2
      className={cn(
        "text-sm font-semibold uppercase tracking-wide text-foreground border-b pb-1.5",
        className,
      )}
    >
      {children}
    </h2>
  );
}
```

- [ ] **Step 2: 验证类型检查**

Run: `pnpm --dir frontend exec tsc -b`
Expected: 0 errors

- [ ] **Step 3: 验证 lint**

Run: `pnpm --dir frontend lint`
Expected: 0 errors（特别确认新文件不产生 unused warning）

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/ui/section-heading.tsx
git commit -m "feat(ui): 抽 SectionTitle/SectionCaption 双组件（M2 / simplify §W 第 1 步）

reading-mode（详情区 h2 lg medium）+ caption（表单/元信息 uppercase border-b）
两形态使用语境不重叠，拆两个组件名直观；下一 commit 替换 5 处 caption 调用点。"
```

---

### Task 5：H2 types feature 中文化

**Files:**
- Modify: `frontend/src/features/types/list/types-table.tsx:31-46`
- Modify: `frontend/src/features/types/form/type-form.tsx:141,156,166,182`
- Modify: `frontend/src/features/types/detail/type-summary-card.tsx:8-29`

- [ ] **Step 1: types-table.tsx 表头改中文**

`types-table.tsx:31-46` 当前：

```tsx
{
  accessorKey: 'name',
  header: 'name',
  cell: ({ row }) => (
    ...
  ),
},
{
  accessorKey: 'code_prefix',
  header: 'code_prefix',
  cell: ({ row }) => (
    <span className="font-mono text-xs">{row.original.code_prefix}</span>
  ),
},
```

改为：

```tsx
{
  accessorKey: 'name',
  header: '名称',
  cell: ({ row }) => (
    ...
  ),
},
{
  accessorKey: 'code_prefix',
  header: '代号前缀',
  cell: ({ row }) => (
    <span className="font-mono text-xs">{row.original.code_prefix}</span>
  ),
},
```

- [ ] **Step 2: type-form.tsx FormLabels 改中文（4 处）**

`type-form.tsx:141`：

```diff
-                  <FormLabel>name *</FormLabel>
+                  <FormLabel>名称 *</FormLabel>
```

`type-form.tsx:156`：

```diff
-                    <FormLabel>code_prefix *</FormLabel>
+                    <FormLabel>代号前缀 *</FormLabel>
```

`type-form.tsx:166`（readonly Label）：

```diff
-                <Label htmlFor="code_prefix-readonly">code_prefix</Label>
+                <Label htmlFor="code_prefix-readonly">代号前缀</Label>
```

`type-form.tsx:182`：

```diff
-                  <FormLabel>description</FormLabel>
+                  <FormLabel>描述</FormLabel>
```

**不动**：`type-form.tsx:109-112` 的 409 错误匹配（`msg.includes('code_prefix')` / `msg.includes('name')` / `form.setError('code_prefix' as never...)`）——这些匹配后端错误消息里的英文字段名 + `name` 是 RHF form key 字面量，与 UI label 无关。

- [ ] **Step 3: type-summary-card.tsx `<dt>` 改中文**

整个文件替换为：

```tsx
import type { components } from '@/api/generated/schema';
import { formatDateTime } from '@/lib/date';

type TypeRead = components['schemas']['TypeRead'];

export function TypeSummaryCard({ type }: { type: TypeRead }) {
  return (
    <dl className="grid grid-cols-2 gap-4 text-sm">
      <div>
        <dt className="text-xs uppercase text-muted-foreground">名称</dt>
        <dd className="font-medium">{type.name}</dd>
      </div>
      <div>
        <dt className="text-xs uppercase text-muted-foreground">代号前缀</dt>
        <dd className="font-mono">{type.code_prefix}</dd>
      </div>
      <div className="col-span-2">
        <dt className="text-xs uppercase text-muted-foreground">描述</dt>
        <dd>{type.description || <span className="text-muted-foreground">—</span>}</dd>
      </div>
      <div>
        <dt className="text-xs uppercase text-muted-foreground">创建时间</dt>
        <dd className="text-muted-foreground">{formatDateTime(type.created_at)}</dd>
      </div>
      <div>
        <dt className="text-xs uppercase text-muted-foreground">更新时间</dt>
        <dd className="text-muted-foreground">{formatDateTime(type.updated_at)}</dd>
      </div>
    </dl>
  );
}
```

注：`text-xs uppercase` 在中文 `<dt>` 上 uppercase 无效，是有意保留——为未来若有英文术语穿插（如 ID 行）保持容器一致。

- [ ] **Step 4: 跑测试套件，捕获断言英文 label 的失败用例**

Run: `pnpm --dir frontend test --run`
Expected: 73 passed（如果有用例断言 `getByLabelText('name')` 等英文文本将失败，Step 5 处理）

- [ ] **Step 5: 如有测试失败，同步修改测试断言（不新增测试）**

如果 Step 4 报失败：
- 找到失败测试的具体断言行
- 把英文文本替换为新中文文本（"名称"/"代号前缀"/"描述"）
- 重跑 `pnpm --dir frontend test --run` 至 73 passed
- 如果失败用例不在 types feature 域内（资产端测试不应受影响），停下来人工 review 找原因

- [ ] **Step 6: 验证类型检查 + lint**

Run: `pnpm --dir frontend exec tsc -b`
Expected: 0 errors
Run: `pnpm --dir frontend lint`
Expected: 0 errors

- [ ] **Step 7: 启动 dev server 烟测 types 三页**

`/types` 列表表头：表头列名 "名称 / 代号前缀 / 字段数 / 资产引用"
`/types/new` 表单：FormLabel "名称 *" / "代号前缀 *" / "描述"
`/types/$id` 编辑页：readonly Label "代号前缀"，TypeSummaryCard `<dt>` 全中文

- [ ] **Step 8: Commit**

```bash
git add frontend/src/features/types/list/types-table.tsx \
  frontend/src/features/types/form/type-form.tsx \
  frontend/src/features/types/detail/type-summary-card.tsx
# 如 Step 5 改了测试也一并 add
git commit -m "fix(types): 列表/表单/元信息卡 UI 文本英文标识符 → 中文（H2）

types-table 表头、type-form FormLabel/readonly Label、TypeSummaryCard <dt>
统一改中文，与资产端 COLUMN_LABELS 中文化对齐。
type-form.tsx:109-112 的 409 错误匹配保留英文（匹配后端错误消息）。"
```

---

### Task 6：M2 替换 5 处 caption 调用点

**Files:**
- Modify: `frontend/src/features/assets/form/asset-form-fields.tsx:38-43`
- Modify: `frontend/src/features/assets/form/custom-fields-form.tsx:19-26`
- Modify: `frontend/src/features/types/form/type-form.tsx:131-134, 192-195`
- Modify: `frontend/src/features/types/detail/type-detail-page.tsx:46-49`

- [ ] **Step 1: asset-form-fields.tsx 替换 caption**

`asset-form-fields.tsx:38-43` 当前：

```tsx
return (
  <div className="space-y-10">
    <section className="space-y-4">
      <h2 className="text-sm font-semibold uppercase tracking-wide text-foreground border-b pb-1.5">
        基础信息
      </h2>
```

改为：

```tsx
return (
  <div className="space-y-10">
    <section className="space-y-4">
      <SectionCaption>基础信息</SectionCaption>
```

并在 import 块加：

```tsx
import { SectionCaption } from '@/components/ui/section-heading';
```

- [ ] **Step 2: custom-fields-form.tsx 替换 caption（带额外 children）**

`custom-fields-form.tsx:19-26` 当前的 `<h2>` 内同时有 typeName 和 字段数 badge。SectionCaption 接受 ReactNode children 即可保留两者。

```tsx
return (
  <section className="space-y-4">
    <SectionCaption>
      {typeName}
      <span className="ml-2 rounded-full bg-secondary px-2 text-xs font-normal">
        {fieldDefs.length} 个字段
      </span>
    </SectionCaption>
    ...
  </section>
);
```

并加 import：

```tsx
import { SectionCaption } from '@/components/ui/section-heading';
```

- [ ] **Step 3: type-form.tsx 替换两处 caption**

行 131-134（"基本信息"）：

```diff
-          <section className="space-y-4">
-            <h2 className="text-sm font-semibold uppercase tracking-wide text-foreground border-b pb-1.5">
-              基本信息
-            </h2>
+          <section className="space-y-4">
+            <SectionCaption>基本信息</SectionCaption>
```

行 192-195（"自定义字段"）：

```diff
-          <section className="space-y-4">
-            <h2 className="text-sm font-semibold uppercase tracking-wide text-foreground border-b pb-1.5">
-              自定义字段
-            </h2>
+          <section className="space-y-4">
+            <SectionCaption>自定义字段</SectionCaption>
```

import 块加：

```tsx
import { SectionCaption } from '@/components/ui/section-heading';
```

- [ ] **Step 4: type-detail-page.tsx 替换 caption**

行 46-49（"元信息"）：

```diff
-      <section>
-        <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground mb-3">
-          元信息
-        </h2>
+      <section>
+        <SectionCaption className="text-muted-foreground mb-3">元信息</SectionCaption>
         <TypeSummaryCard type={q.data} />
       </section>
```

注：原 type-detail-page 用的不是完整 caption（缺 `border-b pb-1.5`，且 `text-muted-foreground` 而非 `text-foreground`）。这里**显式传 className 覆盖**保留原有视觉，不强行统一——即"先迁移到组件 + 保留视觉"，未来若决议统一再做。

import 块加：

```tsx
import { SectionCaption } from '@/components/ui/section-heading';
```

- [ ] **Step 5: 验证类型检查**

Run: `pnpm --dir frontend exec tsc -b`
Expected: 0 errors

- [ ] **Step 6: 验证 lint**

Run: `pnpm --dir frontend lint`
Expected: 0 errors

- [ ] **Step 7: 验证测试不受影响**

Run: `pnpm --dir frontend test --run`
Expected: 73 passed

- [ ] **Step 8: dev server 烟测 5 处 caption 视觉无改变**

视觉应与替换前完全一致（uppercase + tracking-wide + border-b 形态）。type-detail-page "元信息" 应保持 muted-foreground 浅色。

- [ ] **Step 9: Commit**

```bash
git add frontend/src/features/assets/form/asset-form-fields.tsx \
  frontend/src/features/assets/form/custom-fields-form.tsx \
  frontend/src/features/types/form/type-form.tsx \
  frontend/src/features/types/detail/type-detail-page.tsx
git commit -m "refactor(ui): 5 处 section caption className 串改用 SectionCaption 组件（M2 / simplify §W）

被替换的位置：asset-form-fields 基础信息 / custom-fields-form typeName +
字段数 / type-form 基本信息 + 自定义字段 / type-detail-page 元信息。
type-detail-page 显式传 muted-foreground className 覆盖保留原视觉。"
```

---

### Task 7：H5 NotFoundPanel 公共化

**Files:**
- Create: `frontend/src/components/feedback/not-found-panel.tsx`
- Create: `frontend/src/features/assets/detail/asset-not-found.tsx`
- Create: `frontend/src/features/types/detail/type-not-found.tsx`
- Modify: `frontend/src/features/assets/detail/asset-detail-page.tsx:20,82`
- Modify: `frontend/src/routes/assets.$id.tsx:3,8`
- Modify: `frontend/src/features/types/detail/type-detail-page.tsx:1-34`
- Delete: `frontend/src/features/assets/detail/not-found-panel.tsx`

- [ ] **Step 1: 创建公共 NotFoundPanel**

`frontend/src/components/feedback/not-found-panel.tsx`：

```tsx
import type { LucideIcon } from "lucide-react";
import { SearchX } from "lucide-react";
import type { ReactNode } from "react";

interface NotFoundPanelProps {
  icon?: LucideIcon;
  title: string;
  description?: string;
  backLink: ReactNode;
}

export function NotFoundPanel({
  icon: Icon = SearchX,
  title,
  description,
  backLink,
}: NotFoundPanelProps) {
  return (
    <div
      role="alert"
      className="mx-auto flex max-w-md flex-col items-center justify-center gap-4 py-24 text-center"
    >
      <Icon className="h-12 w-12 text-muted-foreground" aria-hidden />
      <div className="space-y-1">
        <h2 className="text-xl font-medium">{title}</h2>
        {description ? (
          <p className="text-sm text-muted-foreground">{description}</p>
        ) : null}
      </div>
      <div>{backLink}</div>
    </div>
  );
}
```

注：保留原 asset 版本的 `mx-auto max-w-md py-24 gap-4` + `h-12 w-12` icon + `text-xl font-medium` heading 配置；不改视觉，仅参数化。

- [ ] **Step 2: 创建 asset-not-found.tsx wrapper**

`frontend/src/features/assets/detail/asset-not-found.tsx`：

```tsx
import { Link } from "@tanstack/react-router";
import { Button } from "@/components/ui/button";
import { NotFoundPanel } from "@/components/feedback/not-found-panel";
import { ASSETS_DEFAULT_SEARCH } from "@/features/assets/list/search-schema";

export function AssetNotFound() {
  return (
    <NotFoundPanel
      title="资产不存在"
      description="它可能已被删除，或链接有误。"
      backLink={
        <Link to="/" search={ASSETS_DEFAULT_SEARCH}>
          <Button variant="outline">返回列表</Button>
        </Link>
      }
    />
  );
}
```

注：从 `search-schema.ts` 导入 `ASSETS_DEFAULT_SEARCH` 替代原 inline `{ sort: 'asset_code', page: 1, pageSize: 50 }`，去掉一处魔法对象。

- [ ] **Step 3: 创建 type-not-found.tsx wrapper**

`frontend/src/features/types/detail/type-not-found.tsx`：

```tsx
import { Link } from "@tanstack/react-router";
import { Button } from "@/components/ui/button";
import { NotFoundPanel } from "@/components/feedback/not-found-panel";

export function TypeNotFound() {
  return (
    <NotFoundPanel
      title="该类型不存在"
      description="可能已被删除，或链接有误。"
      backLink={
        <Button asChild variant="outline">
          <Link to="/types">返回类型列表</Link>
        </Button>
      }
    />
  );
}
```

- [ ] **Step 4: asset-detail-page.tsx 改 import 与调用**

行 20：

```diff
- import { NotFoundPanel } from "./not-found-panel";
+ import { AssetNotFound } from "./asset-not-found";
```

行 82：

```diff
-     return <NotFoundPanel />;
+     return <AssetNotFound />;
```

- [ ] **Step 5: routes/assets.$id.tsx 改 import 与 errorComponent**

```diff
- import { NotFoundPanel } from "@/features/assets/detail/not-found-panel";
+ import { AssetNotFound } from "@/features/assets/detail/asset-not-found";

  export const Route = createFileRoute("/assets/$id")({
    parseParams: ({ id }) => ({ id: z.string().uuid().parse(id) }),
    component: () => <Outlet />,
-   errorComponent: NotFoundPanel,
+   errorComponent: AssetNotFound,
  });
```

- [ ] **Step 6: type-detail-page.tsx 替换内联 404 块**

当前 `type-detail-page.tsx:1-34`：

```tsx
import { useState } from 'react';
import { Link, useNavigate } from '@tanstack/react-router';
import { SearchX, Trash2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { ErrorState } from '@/components/feedback/error-state';
import { Skeleton } from '@/components/ui/skeleton';
import { isHttpError } from '@/lib/error';
import { useTypeQuery } from '@/api/hooks/types';
import { TypeSummaryCard } from './type-summary-card';
import { TypeDeleteDialog } from './type-delete-dialog';
import { TypeForm } from '../form/type-form';

export function TypeDetailPage({ id }: { id: string }) {
  const navigate = useNavigate();
  const q = useTypeQuery(id);
  const [deleting, setDeleting] = useState(false);

  if (q.isLoading) return <Skeleton className="h-96 w-full" />;
  if (q.isError) {
    const is404 = isHttpError(q.error) && q.error.status === 404;
    if (is404) {
      return (
        <div className="flex flex-col items-center gap-3 py-16 text-muted-foreground">
          <SearchX className="h-10 w-10" />
          <p>该类型不存在</p>
          <Button asChild variant="outline">
            <Link to="/types">返回类型列表</Link>
          </Button>
        </div>
      );
    }
    return <ErrorState error={q.error} onRetry={() => q.refetch()} />;
  }
```

改为：

```tsx
import { useState } from 'react';
import { useNavigate } from '@tanstack/react-router';
import { Trash2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { ErrorState } from '@/components/feedback/error-state';
import { Skeleton } from '@/components/ui/skeleton';
import { isHttpError } from '@/lib/error';
import { useTypeQuery } from '@/api/hooks/types';
import { TypeSummaryCard } from './type-summary-card';
import { TypeDeleteDialog } from './type-delete-dialog';
import { TypeNotFound } from './type-not-found';
import { TypeForm } from '../form/type-form';

export function TypeDetailPage({ id }: { id: string }) {
  const navigate = useNavigate();
  const q = useTypeQuery(id);
  const [deleting, setDeleting] = useState(false);

  if (q.isLoading) return <Skeleton className="h-96 w-full" />;
  if (q.isError) {
    const is404 = isHttpError(q.error) && q.error.status === 404;
    if (is404) return <TypeNotFound />;
    return <ErrorState error={q.error} onRetry={() => q.refetch()} />;
  }
```

import 变更要点：删 `Link` / `SearchX` / `Trash2 → 改为只 Trash2`（但 Trash2 仍在底下"删除类型"按钮用，保留），实际净变化：
- 删 `Link` import（已不需）
- 删 `SearchX` import（已不需）
- 加 `TypeNotFound` import

`Trash2` / `Button` / `useNavigate` 仍然需要（删除按钮 + 删除回调）。

- [ ] **Step 7: 删除 asset-private not-found-panel.tsx**

```bash
rm frontend/src/features/assets/detail/not-found-panel.tsx
```

- [ ] **Step 8: 验证类型检查**

Run: `pnpm --dir frontend exec tsc -b`
Expected: 0 errors

- [ ] **Step 9: 验证 lint（重点检查 unused imports）**

Run: `pnpm --dir frontend lint`
Expected: 0 errors

- [ ] **Step 10: 验证测试不受影响**

Run: `pnpm --dir frontend test --run`
Expected: 73 passed

- [ ] **Step 11: dev server 烟测两个 404 场景**

- 浏览 `/assets/00000000-0000-0000-0000-000000000000`：显示 "资产不存在" + "返回列表" 按钮
- 浏览 `/types/00000000-0000-0000-0000-000000000000`：显示 "该类型不存在" + "返回类型列表" 按钮
- 两个 panel 视觉一致（icon size / heading size / 间距），仅文案 / 跳转目的地不同

- [ ] **Step 12: Commit**

```bash
git add frontend/src/components/feedback/not-found-panel.tsx \
  frontend/src/features/assets/detail/asset-not-found.tsx \
  frontend/src/features/types/detail/type-not-found.tsx \
  frontend/src/features/assets/detail/asset-detail-page.tsx \
  frontend/src/features/types/detail/type-detail-page.tsx \
  frontend/src/routes/assets.$id.tsx
git rm frontend/src/features/assets/detail/not-found-panel.tsx
git commit -m "refactor(feedback): NotFoundPanel 提到公共组件 + 资产/类型各写 thin wrapper（H5 / simplify §U）

公共组件接 backLink: ReactNode slot，不让 TanStack Router strict typing
穿透到公共层；asset/type wrapper 各自承载 typed Link。
asset-detail-page errorComponent / inline 404 + type-detail-page inline 404
全部替换。"
```

---

### Task 8：MASTER 实施期纠偏 + simplify §7 + followup-allocation

**Files:**
- Modify: `design-system/asset-hub/MASTER.md`（追加 "M2 视觉收尾（2026-05-03）" 节）
- Modify: `docs/superpowers/simplify-followups.md`（追加 §7）
- Modify: `docs/superpowers/followup-allocation.md`（§M3 强搭车表加一行）

- [ ] **Step 1: MASTER 追加实施期纠偏节**

在 `design-system/asset-hub/MASTER.md` 末尾追加（沿用现有 §M2c-1 / §M2c-2 / §M2c-3 体例）：

```markdown
---

## 实施期纠偏（M2 视觉收尾，2026-05-03）

frontend-design skill 对 M2a→M2c-4 全栈做了一次设计契约对照审计（见 [`docs/superpowers/specs/2026-05-03-m2-visual-polish-design.md`](../../docs/superpowers/specs/2026-05-03-m2-visual-polish-design.md)）。本里程碑闭环 H 类全部 + M2 SectionHeading；以下是新写入的覆盖 / 决议。

### 1. H1 · 放弃 "Heading: Fira Code" 承诺（D 路径）

**原承诺**：MASTER §Typography "Heading Font: Fira Code"，spec m2c1 §3.5.3 字体合规表 "Heading 字体 Fira Code"。
**实际情况**：Fira Code 不渲染中文，UI 中所有 heading（"小组资产管理工具" / "通用字段" / "基本信息"）都走 PingFang fallback；唯一能见到 Fira Code 效果的是英文 h1（如资产名）；视觉对比表明三方案在中文 UI 下几乎无差异。
**决议**：删 `globals.css --font-heading` token，spec/MASTER 改成 "Heading: Fira Sans；Fira Code 仅用于 mono 字段"。
**实施**：M2 视觉收尾 PR Task 1，commit ref 见 git log。

### 2. H2 · types feature UI 文本英文 → 中文

**问题**：types-table 表头 / type-form FormLabel / TypeSummaryCard `<dt>` 用 `name` / `code_prefix` / `description` 字段标识符当 UI 文本，与资产端中文化（COLUMN_LABELS）不一致。
**决议**：替换为 "名称 / 代号前缀 / 描述 / 创建时间 / 更新时间"；`code_prefix` 等字段在 input 内继续走 `font-mono`，"代号前缀" 语义靠中文 label 表达。
**实施**：M2 视觉收尾 PR Task 5。

### 3. H3 · CheckoutTimeline 状态色改 token

**问题**：`bg-[var(--status-active,#16a34a)]/10` 中 `--status-active` 从未定义，每次回落到 hex `#16a34a`，绕开 OKLCH dark-mode 独立调机制。
**决议**：改用已存在的 `--status-in-use` / `--status-in-use-fg` token；不为"派发中"单独建 `--status-active`。
**实施**：M2 视觉收尾 PR Task 3。

### 4. H4 · TypesPage 接 EmptyState

**问题**：内联 `flex flex-col items-center gap-3 py-16` + Inbox + Button 与公共 EmptyState 视觉骨架重复。
**决议**：改用 `<EmptyState title description action>`。
**实施**：M2 视觉收尾 PR Task 2。

### 5. H5 · NotFoundPanel 公共化（C 路径）

**问题**：asset-private NotFoundPanel + type-detail-page 内联同款骨架，2 倍化触发抽公共组件。
**决议**：lift 到 `components/feedback/not-found-panel.tsx`，接 `backLink: ReactNode` slot；assets/types 各写 thin wrapper 承载 typed Link。
**实施**：M2 视觉收尾 PR Task 7。

### 6. M2 · SectionHeading 抽双组件

**问题**：simplify §W 登记的 5 处 section caption className 串复制。
**决议**：拆 `<SectionTitle>`（详情阅读区 lg medium）+ `<SectionCaption>`（表单/元信息 uppercase border-b）双组件。本 PR 只替换 5 处 caption；reading-mode 形态保持现状。
**实施**：M2 视觉收尾 PR Task 4 + Task 6。

### 7. 未做项（登记到 simplify §7）

- M1 TypesTable 未接 Motion 三时刻 — M3 决议
- M3 页面 H1 字号三档无 type scale token — M3 看板/导出加 h1 时一并约定
- M4 attachment-grid `transition-shadow` 配错 prop 名 — M3 触碰附件 grid 时顺手
```

- [ ] **Step 2: simplify-followups.md 追加 §7**

在文件末尾追加（沿用 §1-§6 体例）：

```markdown
---

## §7 M2 视觉收尾审计未选项（2026-05-03）

**视角**：frontend-design skill 对照 ui-ux-pro-max MASTER + spec §3.5 做的 M2 阶段全栈审计；本 PR（M2 视觉收尾，[2026-05-03 spec](./specs/2026-05-03-m2-visual-polish-design.md)）闭环了 H 类全部 + M2 SectionHeading，以下是当时记录暂不动的项。

### M1 · TypesTable 未接 Motion 三时刻（stagger / tbody-fade）

**位置**：`frontend/src/features/types/list/types-table.tsx:124`

**现状**：资产表 `tbody key={bodyKey} className="tbody-fade"` + `<tr className="stagger-row" style={animationDelay}>`（assets-table.tsx:249-254），类型表 `<tbody>` 干净无 motion。

**ROI**：低。类型 N≪资产 N（v1 类型预计 <20，资产 <500），stagger 对类型表几乎没视觉收益；不接亦不影响 spec §3.5.5 "三时刻"承诺（时刻 1 适用对象本就是"列表首屏"，types 列表首屏可独立判定）。

**风险**：低。接入 5 行 diff，纯前端。

**何时做**：M3 启动时，如类型管理也要做"首屏入场感"统一，再补；若 M3 决定"types 列表故意保持静态"，把决议写进 MASTER 实施期纠偏。

---

### M3 · 页面 H1 字号三档无 type scale token

**位置**：
- `features/assets/detail/asset-header.tsx:57` `text-2xl font-semibold`
- `features/types/list/types-page.tsx:22` `text-xl font-semibold`
- `features/types/detail/type-detail-page.tsx:39` `text-xl font-semibold`

**现状**：每页 h1 字号各凭手感，无统一规则。

**ROI**：中。固化 "列表/详情 h1 字号约定" 防新增页面再加第 4 档；改动 trivial（约 5 行）。

**风险**：低。不动现有视觉效果（除非选定值与现有不一致）。

**何时做**：M3 看板页 + 导出页加 h1 时一并约定，避免每加一页判一次。届时定 utility class（如 `.text-page-title`）或在 `globals.css` 加 type scale 节。

---

### M4 · `attachment-grid` `transition-shadow` 配错 prop 名

**位置**：`frontend/src/features/assets/detail/attachment-grid.tsx:54`

**现状**：`className="... transition-shadow hover:ring-2 hover:ring-primary/40"`。`transition-shadow` 监听 `box-shadow`；hover 用的是 `ring-*`（在浏览器底层是 box-shadow 实现），所以"凑巧能用"，但语义错。

**ROI**：极低。1 行修改；视觉无变化（只是 transition 触发更精准）。

**风险**：极低（trivial）。

**何时做**：M3 任意触碰附件 grid 时顺手吃掉；不值得单独 PR。
```

同时在文件顶部 §索引节中加入新条目：

```diff
 - [§5 M2d 范围（2026-04-29）](#5-m2d-范围2026-04-29)
 - [§6 M2c-4 范围（2026-04-30）](#6-m2c-4-范围2026-04-30)
+- [§7 M2 视觉收尾审计未选项（2026-05-03）](#7-m2-视觉收尾审计未选项2026-05-03)
```

- [ ] **Step 3: followup-allocation.md §M3 强搭车表加一行**

在 `followup-allocation.md` §M3 表（行 55-63）追加最后一行：

```diff
 | **§14.8** timeline 视觉重构（时间渐隐 + 派出类型染色 + 超长派发预警） | spec | 已登记"M3 与 14.1 联动" |
+| **simplify §7（M1/M3/M4）** M2 视觉收尾审计未选项 | M2 视觉审计 | TypesTable motion 决议 / 页面 h1 type scale / attachment transition prop fix；M3 启动时一并扫 |
```

- [ ] **Step 4: 验证渲染（基本 lint 文档）**

不需要技术验证。git diff 自检 markdown 格式无破损（标题层级 / 链接锚点）。

- [ ] **Step 5: Commit**

```bash
git add design-system/asset-hub/MASTER.md \
  docs/superpowers/simplify-followups.md \
  docs/superpowers/followup-allocation.md
git commit -m "docs(simplify): M2 视觉收尾纠偏 + simplify §7 未选项 + followup-allocation §M3 加一行

MASTER 追加 \"M2 视觉收尾（2026-05-03）\" 实施期纠偏节，回写 H1-5 + M2 决议。
simplify-followups §7 登记未做项 M1/M3/M4 + 索引补一行。
followup-allocation §M3 强搭车表加一行指向 §7。"
```

---

### Task 9：最终验证（红线扫描 + 完整测试套件 + 全场景烟测）

**Files:**
- 不修改任何文件，纯验证。

- [ ] **Step 1: 红线扫描**

```bash
grep -rnE "scale-|animate-spin|backdrop-blur|bg-gradient-to|font-family.*Inter|font-family.*Roboto|font-family.*Geist" frontend/src/
```

Expected: 0 命中（与 M2c-1/2/3/4 历次实施期保持一致）

- [ ] **Step 2: --font-heading 残留扫描**

```bash
grep -rn "font-heading\|--font-heading" frontend/ docs/ design-system/ 2>&1 | grep -v node_modules
```

Expected: 0 命中（除 m2-visual-polish-design.md 中作为历史叙事的引用外；如果 m2c1 spec 里仍残留 token 表，需要回溯 Task 1 Step 2）

- [ ] **Step 3: 完整测试套件**

```bash
pnpm --dir frontend test --run
pnpm --dir frontend exec tsc -b
pnpm --dir frontend lint
uv run pytest
uv run ruff check .
```

Expected:
- frontend test: 73 passed (16 files)
- tsc: 0 errors
- frontend lint: 0 errors
- pytest: 311 passed + 1 skipped (M2c-4 验证基准)
- ruff: All checks passed

- [ ] **Step 4: dev server 全场景烟测（按 spec §4 验证表）**

启动：`uv run asset-hub serve start --mode dev`（或 `pnpm --dir frontend dev` + 后端独立启动）

| # | 路径 | 验证点 |
|---|---|---|
| 1 | `/` 资产列表 | 表头与导航文案不变、stagger reveal 正常 |
| 2 | 点资产名进 `/assets/$id` | 详情页所有 h2（reading-mode "通用字段" / "附件" / "流转记录"）显示正常 |
| 3 | IN_USE 资产详情 timeline | "派发中" pill 浅绿 token 色（不再是 emerald-600 hex） |
| 4 | 切深色模式 | timeline pill 暗绿、对比正确；其他 section 色调一致性正常 |
| 5 | `/types`（如数据为 0） | EmptyState 三段（Inbox icon + "还没有类型" + description + 按钮） |
| 6 | `/types/new` 表单 | FormLabel "名称 *" / "代号前缀 *" / "描述"；section caption "基本信息" / "自定义字段" 中文 + uppercase border-b |
| 7 | `/types/$id` 编辑页 | TypeSummaryCard `<dt>` 全中文、SectionCaption "元信息" muted 色 |
| 8 | `/types/00000000-...` UUID | TypeNotFound：SearchX + "该类型不存在" + "返回类型列表" |
| 9 | `/assets/00000000-...` UUID | AssetNotFound：SearchX + "资产不存在" + "返回列表" |
| 10 | 所有 caption 5 处 | 与替换前视觉完全一致（uppercase + tracking-wide + border-b 形态） |

- [ ] **Step 5: 不 commit（验证 task）**

如全部 PASS，本 PR 已就绪。如 dev server 烟测发现视觉偏差（特别 Task 3 timeline 颜色 / Task 7 NotFoundPanel 间距），回到对应 Task fix。

---

## 收尾

PR 总改动量预估：~120 行代码 + 3 个文档段落，9 个 commit。

**建议 PR 标题**：`refactor(visual): M2 视觉收尾（H1-5 + M2 SectionHeading）`

**PR 描述**：链接 [`docs/superpowers/specs/2026-05-03-m2-visual-polish-design.md`](../specs/2026-05-03-m2-visual-polish-design.md)；按 9 个 Task 顺序列改动；附 spec §4 验证表 checklist。

合并后：

- M3 brainstorm 启动时阅读 `simplify-followups.md` §7 + `followup-allocation.md` §M3 决定 M1/M3/M4 是否搭车
- 设计契约审计作为流程留存：今后每个里程碑合并后由作者主动跑一次 frontend-design 审计，审计报告对应未闭环项进 simplify-followups.md 新增 §N
