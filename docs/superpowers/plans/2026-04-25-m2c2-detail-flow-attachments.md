# M2c-2 · 详情 + 流转 + 附件查看 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 基于 [`docs/superpowers/specs/2026-04-25-m2c2-detail-flow-attachments-design.md`](../specs/2026-04-25-m2c2-detail-flow-attachments-design.md)，交付路由 `/assets/:id` 上可交互的资产详情页：Header + 通用字段 + 类型字段 + 附件查看 + 流转时间线 + 派发/归还/删除附件 3 条 mutation；同时接通 M2c-1 列表页 ⋯ 菜单的派发/归还动作。

**Architecture:** 严格按 spec §4：单列 stacked 布局 + 三层继承 M2c-1（api layer / theme / feedback / StatusBadge 全复用）；数据层纯前端推导当前派发（`deriveCurrentCheckout`）；Dialog 用纯 React state + 手工校验（M2c-3 再迁 RHF）；**§3.4.1 MASTER override** 显式：spinner 改文字切换 + 骨架、禁 backdrop-blur、不用 Card 装饰、不用 `<Separator />`。**无 Vitest**（spec §9）——每 Task 验证 = `pnpm build` + `pnpm lint` + 手工观察（浏览器）。

**Tech Stack:** React 19 + TypeScript strict + TanStack Router/Query + openapi-fetch + shadcn（radix-nova style）+ sonner + lucide-react + date-fns + pnpm（继承 M2c-1，无新增 npm 依赖）

**Spec 引用约定：** 每个 UI-ish Task 末尾的 `**§3.5 约束引用**` 栏列出该 Task 必须满足的 spec 条目（同 M2c-1 plan 约定）。

---

## 文件结构

M2c-2 完成后前端新增/修改的文件：

```
frontend/
├── src/
│   ├── api/
│   │   ├── query-keys.ts                # 修：+history / +attachments.byAsset key factory
│   │   └── hooks/
│   │       ├── assets.ts                # 修：+useAssetDetailQuery
│   │       ├── checkouts.ts             # 新：history query + checkout/return mutation
│   │       └── attachments.ts           # 新：list query + delete mutation
│   ├── routes/
│   │   └── assets.$id.tsx               # 新：file-based detail 路由
│   ├── features/assets/
│   │   ├── detail/
│   │   │   ├── asset-detail-page.tsx    # 新
│   │   │   ├── asset-header.tsx         # 新
│   │   │   ├── current-checkout.ts      # 新（纯函数）
│   │   │   ├── general-fields.tsx       # 新
│   │   │   ├── custom-fields.tsx        # 新
│   │   │   ├── custom-field-formatter.ts # 新（纯函数）
│   │   │   ├── attachment-grid.tsx      # 新
│   │   │   ├── attachment-lightbox.tsx  # 新
│   │   │   ├── checkout-timeline.tsx    # 新
│   │   │   ├── checkout-dialog.tsx      # 新
│   │   │   ├── return-dialog.tsx        # 新
│   │   │   ├── checkout-actions.ts      # 新（verb 常量 + M3 扩展位）
│   │   │   ├── not-found-panel.tsx      # 新
│   │   │   └── detail-skeleton.tsx      # 新
│   │   └── list/
│   │       └── assets-table.tsx         # 修：RowActions 接线派发/归还 + AssetListPage 顶层 Dialog 状态
│   └── routes/
│       └── index.tsx                    # 修：lift Dialog 状态 + 传给 AssetsTable
└── components/ui/
    ├── dialog.tsx                       # shadcn add
    └── alert-dialog.tsx                 # shadcn add
```

**统计：新增 17 个文件（routes 1 + hooks 2 + features/assets/detail 14）、修改 4 个文件、shadcn add 2 个组件**。

（spec §4.2 原写"16 新增"，遗漏了 `detail-skeleton.tsx`；本 plan 修正为 17 并同步回写 spec §4.2 + §11 DoD。）

后端**零改动**。

---

## Task 1: queryKey 扩展 + 3 个 read hooks

**Files:**
- Modify: `frontend/src/api/query-keys.ts`
- Modify: `frontend/src/api/hooks/assets.ts`
- Create: `frontend/src/api/hooks/checkouts.ts`
- Create: `frontend/src/api/hooks/attachments.ts`

- [ ] **Step 1：扩展 `query-keys.ts`**

```ts
// frontend/src/api/query-keys.ts
import type { AssetsSearch } from "@/features/assets/list/search-schema";

export const qk = {
  assets: {
    all: ["assets"] as const,
    list: (params: AssetsSearch) => ["assets", "list", params] as const,
    detail: (id: string) => ["assets", "detail", id] as const,
    history: (id: string) => ["assets", id, "history"] as const,
  },
  assetTypes: {
    all: ["assetTypes"] as const,
    list: () => ["assetTypes", "list"] as const,
  },
  attachments: {
    byAsset: (assetId: string) =>
      ["attachments", "byAsset", assetId] as const,
  },
} as const;
```

- [ ] **Step 2：`useAssetDetailQuery` 追加到 `hooks/assets.ts` 末尾**

```ts
// frontend/src/api/hooks/assets.ts 追加在文件末尾
export function useAssetDetailQuery(id: string) {
  return useQuery({
    queryKey: qk.assets.detail(id),
    queryFn: async () => {
      const res = await http.GET("/api/assets/{asset_id}", {
        params: { path: { asset_id: id } },
      });
      return unwrap(res);
    },
    // 404 靠 errorComponent / isError 分支处理，不在此重试
  });
}
```

- [ ] **Step 3：新建 `hooks/checkouts.ts`（先只含 history query；mutation 在 Task 2）**

```ts
// frontend/src/api/hooks/checkouts.ts
import { useQuery } from "@tanstack/react-query";
import { http } from "@/api/client";
import { qk } from "@/api/query-keys";
import { unwrap } from "@/lib/error";

export function useCheckoutHistoryQuery(assetId: string) {
  return useQuery({
    queryKey: qk.assets.history(assetId),
    queryFn: async () => {
      const res = await http.GET("/api/assets/{asset_id}/history", {
        params: { path: { asset_id: assetId } },
      });
      return unwrap(res);
    },
  });
}
```

- [ ] **Step 4：新建 `hooks/attachments.ts`（先只含 list query；mutation 在 Task 2）**

```ts
// frontend/src/api/hooks/attachments.ts
import { useQuery } from "@tanstack/react-query";
import { http } from "@/api/client";
import { qk } from "@/api/query-keys";
import { unwrap } from "@/lib/error";

export function useAttachmentsQuery(assetId: string) {
  return useQuery({
    queryKey: qk.attachments.byAsset(assetId),
    queryFn: async () => {
      const res = await http.GET("/api/assets/{asset_id}/attachments", {
        params: { path: { asset_id: assetId } },
      });
      return unwrap(res);
    },
  });
}
```

- [ ] **Step 5：验证**

```bash
pnpm --dir frontend build && pnpm --dir frontend lint
```

Expected: 0 TypeScript 错误、0 lint 错误。新 hook 没有被调用但必须编译通过。

- [ ] **Step 6：Commit**

```bash
git add frontend/src/api/query-keys.ts frontend/src/api/hooks/assets.ts frontend/src/api/hooks/checkouts.ts frontend/src/api/hooks/attachments.ts
git commit -m "feat(frontend): M2c-2 read hooks——detail/history/attachments + queryKey 扩展"
```

---

## Task 2: 3 个 write hooks（mutation + 失效策略）

**Files:**
- Modify: `frontend/src/api/hooks/checkouts.ts`
- Modify: `frontend/src/api/hooks/attachments.ts`

**关键约束**：spec §7.7 要求 mutation 失败走 Dialog inline banner，**不弹 Toast**——但全局 `queryClient.mutations.onError` 默认弹 toast。因此新 mutation 必须显式 `onError: () => {}` 压制全局默认；callsite 用 `mutateAsync().catch(setBannerError)`。

- [ ] **Step 1：`useCheckoutMutation` / `useReturnMutation` 追加到 `hooks/checkouts.ts`**

```ts
// frontend/src/api/hooks/checkouts.ts 追加
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import type { components } from "@/api/generated/schema";

export function useCheckoutMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (args: {
      assetId: string;
      body: components["schemas"]["CheckoutCreate"];
    }) => {
      const res = await http.POST("/api/assets/{asset_id}/checkout", {
        params: { path: { asset_id: args.assetId } },
        body: args.body,
      });
      return unwrap(res);
    },
    onSuccess: (_data, { assetId }) => {
      qc.invalidateQueries({ queryKey: qk.assets.all });
      qc.invalidateQueries({ queryKey: qk.assets.detail(assetId) });
      qc.invalidateQueries({ queryKey: qk.assets.history(assetId) });
      toast.success("派发成功");
    },
    // 压制全局默认的 toast.error——Dialog 走 inline banner
    onError: () => {},
  });
}

export function useReturnMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (args: {
      assetId: string;
      body: components["schemas"]["CheckoutReturn"];
    }) => {
      const res = await http.POST("/api/assets/{asset_id}/return", {
        params: { path: { asset_id: args.assetId } },
        body: args.body,
      });
      return unwrap(res);
    },
    onSuccess: (_data, { assetId }) => {
      qc.invalidateQueries({ queryKey: qk.assets.all });
      qc.invalidateQueries({ queryKey: qk.assets.detail(assetId) });
      qc.invalidateQueries({ queryKey: qk.assets.history(assetId) });
      toast.success("归还成功");
    },
    onError: () => {},
  });
}
```

- [ ] **Step 2：`useDeleteAttachmentMutation` 追加到 `hooks/attachments.ts`**

```ts
// frontend/src/api/hooks/attachments.ts 追加
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

export function useDeleteAttachmentMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (args: { attachmentId: string; assetId: string }) => {
      const res = await http.DELETE("/api/attachments/{attachment_id}", {
        params: { path: { attachment_id: args.attachmentId } },
      });
      // 204 返回无 body，openapi-fetch 会给 data=undefined。这里不能用 unwrap（unwrap 要求 data 存在）
      if (res.error) {
        const detail =
          typeof res.error === "object" && res.error !== null
            ? (res.error as { detail?: string }).detail
            : undefined;
        throw { status: res.response.status, detail };
      }
      // 成功返回，无 body
    },
    onSuccess: (_data, { assetId }) => {
      qc.invalidateQueries({ queryKey: qk.attachments.byAsset(assetId) });
      toast.success("附件已删除");
    },
    onError: () => {},
  });
}
```

- [ ] **Step 3：验证**

```bash
pnpm --dir frontend build && pnpm --dir frontend lint
```

- [ ] **Step 4：Commit**

```bash
git add frontend/src/api/hooks/checkouts.ts frontend/src/api/hooks/attachments.ts
git commit -m "feat(frontend): M2c-2 write hooks——checkout/return/deleteAttachment + 失效策略 + 压制全局 toast.error"
```

---

## Task 3: shadcn add `dialog` + `alert-dialog` + variant 审查

**Files:**
- Create: `frontend/src/components/ui/dialog.tsx`（shadcn 生成）
- Create: `frontend/src/components/ui/alert-dialog.tsx`（shadcn 生成）

**§3.5 约束引用：** §3.5.7（shadcn 引入即审）+ §3.4.1 MASTER override（`Dialog.Overlay` 改 `bg-black/50` 不 blur）。

- [ ] **Step 1：shadcn add**

```bash
cd frontend && pnpm dlx shadcn@latest add dialog alert-dialog
```

Expected: `components/ui/dialog.tsx` + `components/ui/alert-dialog.tsx` 生成。

- [ ] **Step 2：审查两个文件的 Overlay 类名**

打开 `dialog.tsx` 和 `alert-dialog.tsx`，定位 `Overlay` 组件的 className。shadcn 默认会生成类似：

```tsx
className={cn(
  "fixed inset-0 z-50 bg-black/80 ... data-[state=open]:animate-in ..."
)}
```

**修改两处**：
- `bg-black/80` → `bg-black/50`
- 确认无 `backdrop-blur-*` 类名（shadcn 默认不带 blur，但以防万一）

- [ ] **Step 3：移除 Next-only 残留**

检查两个文件首行，若有 `"use client"` 指令**直接删除**（Vite + React 19 不需要，M2c-1 清理先例见 `2026-04-24-m2c1-...md` 纠偏 §5）。

- [ ] **Step 4：验证**

```bash
pnpm --dir frontend build && pnpm --dir frontend lint
```

- [ ] **Step 5：红线扫描**

```bash
grep -n "backdrop-blur\|bg-black/80" frontend/src/components/ui/dialog.tsx frontend/src/components/ui/alert-dialog.tsx
```

Expected: 0 命中。

- [ ] **Step 6：Commit**

```bash
git add frontend/src/components/ui/dialog.tsx frontend/src/components/ui/alert-dialog.tsx frontend/components.json 2>/dev/null
git commit -m "feat(frontend): shadcn add dialog + alert-dialog（§3.5.7 审查：overlay 改 bg-black/50、去 Next 残留）"
```

---

## Task 4: 两个纯函数模块（`current-checkout.ts` + `custom-field-formatter.ts`）

**Files:**
- Create: `frontend/src/features/assets/detail/current-checkout.ts`
- Create: `frontend/src/features/assets/detail/custom-field-formatter.ts`

- [ ] **Step 1：`current-checkout.ts`**

```ts
// frontend/src/features/assets/detail/current-checkout.ts
import type { components } from "@/api/generated/schema";

type CheckoutRead = components["schemas"]["CheckoutRead"];

/**
 * 从流转 history 中找出"当前进行中"的派发记录。
 * 不变量：service 层保证同一资产同一时刻最多 1 条 returned_at === null。
 */
export function deriveCurrentCheckout(
  history: CheckoutRead[] | undefined,
): CheckoutRead | null {
  if (!history) return null;
  return history.find((c) => c.returned_at === null) ?? null;
}
```

- [ ] **Step 2：`custom-field-formatter.ts`**

```tsx
// frontend/src/features/assets/detail/custom-field-formatter.ts
import { format, parseISO } from "date-fns";
import { Check, X } from "lucide-react";
import type { ReactNode } from "react";

export type CustomFieldDef = {
  key: string;
  label: string;
  type: "string" | "text" | "int" | "float" | "bool" | "enum" | "date";
  required?: boolean;
  unique?: boolean;
  options?: string[];
};

/**
 * 按 def.type 格式化 custom_data 的 value。
 *
 * 兼容层：
 * - value == null/undefined → "—"
 * - 类型不匹配（脏数据）→ String(value) + "（数据格式异常）"
 */
export function formatCustomFieldValue(
  def: CustomFieldDef,
  value: unknown,
): ReactNode {
  if (value === null || value === undefined) {
    return <span className="text-muted-foreground">—</span>;
  }
  try {
    switch (def.type) {
      case "string":
        return String(value);
      case "text":
        return (
          <span className="whitespace-pre-wrap">{String(value)}</span>
        );
      case "int":
      case "float":
        if (typeof value !== "number")
          throw new Error("expected number");
        return new Intl.NumberFormat("zh-CN").format(value);
      case "bool":
        return value ? (
          <Check
            className="inline-block h-4 w-4 text-[var(--status-active,#16a34a)]"
            aria-label="是"
          />
        ) : (
          <X
            className="inline-block h-4 w-4 text-muted-foreground"
            aria-label="否"
          />
        );
      case "date":
        if (typeof value !== "string")
          throw new Error("expected ISO string");
        return (
          <time className="font-code">
            {format(parseISO(value), "yyyy-MM-dd")}
          </time>
        );
      case "enum":
        return String(value);
      default:
        return String(value);
    }
  } catch {
    return (
      <span>
        {String(value)}{" "}
        <small className="text-muted-foreground">（数据格式异常）</small>
      </span>
    );
  }
}
```

> 注意：本文件以 `.ts` 结尾但含 JSX——会触发 lint/ts 错误。**改文件扩展名为 `.tsx`**。

实际路径改为：`frontend/src/features/assets/detail/custom-field-formatter.tsx`。后续引用统一写 `from "./custom-field-formatter"`（不带扩展）。

- [ ] **Step 3：验证**

```bash
pnpm --dir frontend build && pnpm --dir frontend lint
```

Expected：0 错误。

- [ ] **Step 4：Commit**

```bash
git add frontend/src/features/assets/detail/current-checkout.ts frontend/src/features/assets/detail/custom-field-formatter.tsx
git commit -m "feat(frontend): M2c-2 纯函数——deriveCurrentCheckout + formatCustomFieldValue"
```

---

## Task 5: `checkout-actions.ts`（verb 常量 + M3 扩展位）

**Files:**
- Create: `frontend/src/features/assets/detail/checkout-actions.ts`

**§3.5 约束引用：** §10.1（扩展兼容性——CTA 文字从此处导出不硬编码）。

- [ ] **Step 1：写文件**

```ts
// frontend/src/features/assets/detail/checkout-actions.ts

/**
 * 派发 / 归还动词常量。
 *
 * M2c-2 只支持单一派出类型（组内派发），因此 CTA 文字是字符串常量。
 *
 * M3 扩展"向外出借"（见 spec §10.1）时，CHECKOUT_VERB 升级为：
 *   export const CHECKOUT_TYPES = [
 *     { key: 'internal', verb: '派发', dialogTitle: '组内派发', icon: Users },
 *     { key: 'external', verb: '借出', dialogTitle: '向外出借', icon: ExternalLink },
 *   ] as const
 * CtaButton 同步从 <Button> 升级为 split-button。
 */
export const CHECKOUT_VERB = "派发";
export const RETURN_VERB = "归还";

/** Dialog 标题（与 verb 一致，但分离是为了 M3 扩展时独立变化） */
export const CHECKOUT_DIALOG_TITLE = "派发资产";
export const RETURN_DIALOG_TITLE = "归还资产";

/** mutation pending 时的按钮文字 */
export const CHECKOUT_PENDING_TEXT = "派发中…";
export const RETURN_PENDING_TEXT = "归还中…";
export const DELETE_ATTACHMENT_PENDING_TEXT = "删除中…";
```

- [ ] **Step 2：验证**

```bash
pnpm --dir frontend build && pnpm --dir frontend lint
```

- [ ] **Step 3：Commit**

```bash
git add frontend/src/features/assets/detail/checkout-actions.ts
git commit -m "feat(frontend): checkout-actions 动词常量（M3 派出类型扩展落点）"
```

---

## Task 6: `NotFoundPanel`

**Files:**
- Create: `frontend/src/features/assets/detail/not-found-panel.tsx`

**§3.5 约束引用：** §3.5.1（fewer-but-better）；与 `EmptyState` 视觉同源避免分叉。

- [ ] **Step 1：写文件**

```tsx
// frontend/src/features/assets/detail/not-found-panel.tsx
import { SearchX } from "lucide-react";
import { Link } from "@tanstack/react-router";
import { Button } from "@/components/ui/button";

export function NotFoundPanel() {
  return (
    <div
      role="alert"
      className="mx-auto flex max-w-md flex-col items-center justify-center gap-4 py-24 text-center"
    >
      <SearchX className="h-12 w-12 text-muted-foreground" aria-hidden />
      <div className="space-y-1">
        <h2 className="text-xl font-medium">资产不存在</h2>
        <p className="text-sm text-muted-foreground">
          它可能已被删除，或链接有误。
        </p>
      </div>
      <Link to="/">
        <Button variant="outline">返回列表</Button>
      </Link>
    </div>
  );
}
```

- [ ] **Step 2：验证**

```bash
pnpm --dir frontend build && pnpm --dir frontend lint
```

- [ ] **Step 3：Commit**

```bash
git add frontend/src/features/assets/detail/not-found-panel.tsx
git commit -m "feat(frontend): NotFoundPanel——详情页 404 态与 UUID 非法兜底"
```

---

## Task 7: `DetailSkeleton`

**Files:**
- Create: `frontend/src/features/assets/detail/detail-skeleton.tsx`

**§3.5 约束引用：** §3.4.1 MASTER override（query loading 用骨架代替 spinner）。

- [ ] **Step 1：写文件**

```tsx
// frontend/src/features/assets/detail/detail-skeleton.tsx
import { Skeleton } from "@/components/ui/skeleton";

/**
 * 详情页三态壳的 loading 骨架。
 * 不复用 M2c-1 的 SkeletonRow——那是表格行用的。
 * 模拟详情页的单列结构：Header + 通用字段行 + 附件宫格 + Timeline。
 */
export function DetailSkeleton() {
  return (
    <div className="mx-auto max-w-[960px] space-y-10 px-4 py-8">
      {/* Header */}
      <div className="space-y-2">
        <Skeleton className="h-4 w-24" />
        <Skeleton className="h-7 w-64" />
        <Skeleton className="h-4 w-48" />
      </div>

      {/* 通用字段 8 行 */}
      <div className="space-y-3">
        <Skeleton className="h-6 w-24" />
        {Array.from({ length: 8 }).map((_, i) => (
          <div key={i} className="flex gap-4">
            <Skeleton className="h-4 w-24" />
            <Skeleton className="h-4 w-48" />
          </div>
        ))}
      </div>

      {/* 附件宫格 */}
      <div className="space-y-3">
        <Skeleton className="h-6 w-24" />
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="aspect-square w-full rounded-md" />
          ))}
        </div>
      </div>

      {/* Timeline */}
      <div className="space-y-3">
        <Skeleton className="h-6 w-24" />
        {Array.from({ length: 3 }).map((_, i) => (
          <div key={i} className="flex gap-4">
            <Skeleton className="h-3 w-3 rounded-full" />
            <div className="flex-1 space-y-2">
              <Skeleton className="h-4 w-40" />
              <Skeleton className="h-3 w-64" />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
```

- [ ] **Step 2：验证**

```bash
pnpm --dir frontend build && pnpm --dir frontend lint
```

- [ ] **Step 3：Commit**

```bash
git add frontend/src/features/assets/detail/detail-skeleton.tsx
git commit -m "feat(frontend): DetailSkeleton——详情页 loading 态骨架"
```

---

## Task 8: 路由 `/assets/:id` + `AssetDetailPage` 三态壳（骨架 + 空 body）

**Files:**
- Create: `frontend/src/routes/assets.$id.tsx`
- Create: `frontend/src/features/assets/detail/asset-detail-page.tsx`

**§3.5 约束引用：** §3.5.1 fewer-but-better / §3.5.5 时刻 1（详情页不做 stagger）/ §3.4.1 MASTER override（骨架代替 spinner）。

- [ ] **Step 1：写路由**

```tsx
// frontend/src/routes/assets.$id.tsx
import { createFileRoute } from "@tanstack/react-router";
import { z } from "zod";
import { AssetDetailPage } from "@/features/assets/detail/asset-detail-page";
import { NotFoundPanel } from "@/features/assets/detail/not-found-panel";

export const Route = createFileRoute("/assets/$id")({
  parseParams: ({ id }) => ({ id: z.string().uuid().parse(id) }),
  component: RouteComponent,
  errorComponent: NotFoundPanel,
});

function RouteComponent() {
  const { id } = Route.useParams();
  return <AssetDetailPage id={id} />;
}
```

- [ ] **Step 2：写页面壳（三态 + 空 body 先渲染占位）**

```tsx
// frontend/src/features/assets/detail/asset-detail-page.tsx
import { useAssetDetailQuery } from "@/api/hooks/assets";
import { useCheckoutHistoryQuery } from "@/api/hooks/checkouts";
import { useAttachmentsQuery } from "@/api/hooks/attachments";
import { useAssetTypesQuery } from "@/api/hooks/types";
import { ErrorState } from "@/components/feedback/error-state";
import { DetailSkeleton } from "./detail-skeleton";
import { NotFoundPanel } from "./not-found-panel";
import { isHttpError } from "@/lib/error";

interface AssetDetailPageProps {
  id: string;
}

export function AssetDetailPage({ id }: AssetDetailPageProps) {
  const assetQuery = useAssetDetailQuery(id);
  const historyQuery = useCheckoutHistoryQuery(id);
  const attachmentsQuery = useAttachmentsQuery(id);
  const typesQuery = useAssetTypesQuery();

  if (assetQuery.isLoading) return <DetailSkeleton />;

  if (
    assetQuery.isError &&
    isHttpError(assetQuery.error) &&
    assetQuery.error.status === 404
  ) {
    return <NotFoundPanel />;
  }

  if (assetQuery.isError) {
    return (
      <ErrorState
        error={assetQuery.error}
        onRetry={() => assetQuery.refetch()}
      />
    );
  }

  if (!assetQuery.data) return <DetailSkeleton />;

  const asset = assetQuery.data;
  const assetType = (typesQuery.data ?? []).find((t) => t.id === asset.type_id);

  return (
    <>
      <title>{`${asset.name} · asset-hub`}</title>
      <main className="mx-auto max-w-[960px] space-y-10 px-4 py-8">
        {/* Task 9-12 填充各区块；先占位 */}
        <div className="text-sm text-muted-foreground">
          占位：{asset.name} / {asset.id}
          {assetType ? ` / ${assetType.name}` : ""}
          {historyQuery.isLoading ? " / history 加载中" : ""}
          {attachmentsQuery.isLoading ? " / attachments 加载中" : ""}
        </div>
      </main>
    </>
  );
}
```

> 注意：后续 Task 会把"占位 div"替换为实际区块。本 Task 只验证路由 + 三态壳通路。

- [ ] **Step 3：重新生成路由树**

TanStack Router 需要重新构建 routeTree.gen.ts。触发：

```bash
pnpm --dir frontend dev
```

在浏览器打开 `http://localhost:5173/assets/<任意合法 uuid>` 快速验证，然后 Ctrl+C 关 dev 服务器。

或直接：

```bash
pnpm --dir frontend build
```

会触发 vite plugin 重新生成 routeTree.gen.ts（取决于 M2c-1 的配置，若不自动则需手动跑 `pnpm tsr generate`）。

- [ ] **Step 4：验证**

```bash
pnpm --dir frontend build && pnpm --dir frontend lint
```

手工：启动 `pnpm --dir frontend dev` + 后端 `uv run uvicorn asset_hub.api.app:app --reload`，访问：
- `http://localhost:5173/assets/00000000-0000-0000-0000-000000000000` → NotFoundPanel（假设该 UUID 不存在）
- `http://localhost:5173/assets/not-a-uuid` → NotFoundPanel（UUID 格式错）
- `http://localhost:5173/assets/<一个真实存在的 UUID>`（从列表页取）→ 占位 div 显示 name / id / type

- [ ] **Step 5：Commit**

```bash
git add frontend/src/routes/assets.$id.tsx frontend/src/features/assets/detail/asset-detail-page.tsx frontend/src/routeTree.gen.ts
git commit -m "feat(frontend): /assets/:id 路由 + 三态壳（skeleton/404/error/ok 占位）"
```

---

## Task 9: `AssetHeader` + `CtaButton`（先不接 Dialog）

**Files:**
- Create: `frontend/src/features/assets/detail/asset-header.tsx`
- Modify: `frontend/src/features/assets/detail/asset-detail-page.tsx`

**§3.5 约束引用：** §3.5.3（状态色语义）/ §3.5.5 时刻 2（Button 色变 150-300ms）/ §3.5.6（禁 transform scale）/ §7.2 spec。

- [ ] **Step 1：写 AssetHeader**

```tsx
// frontend/src/features/assets/detail/asset-header.tsx
import { Link } from "@tanstack/react-router";
import { format, parseISO } from "date-fns";
import { Button } from "@/components/ui/button";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { StatusBadge } from "@/components/status/status-badge";
import type { components } from "@/api/generated/schema";
import { CHECKOUT_VERB, RETURN_VERB } from "./checkout-actions";

type AssetRead = components["schemas"]["AssetRead"];
type CheckoutRead = components["schemas"]["CheckoutRead"];

interface AssetHeaderProps {
  asset: AssetRead;
  typeName: string | undefined;
  currentCheckout: CheckoutRead | null;
  onCheckout: () => void;
  onReturn: () => void;
}

export function AssetHeader({
  asset,
  typeName,
  currentCheckout,
  onCheckout,
  onReturn,
}: AssetHeaderProps) {
  return (
    <header className="flex items-start justify-between gap-4">
      <div className="space-y-1">
        <Link
          to="/"
          className="text-sm text-muted-foreground hover:text-foreground transition-colors"
        >
          ← 返回列表
        </Link>
        <h1 className="text-2xl font-semibold">{asset.name}</h1>
        <div className="flex items-center gap-3">
          <span className="text-sm text-muted-foreground">
            {typeName ?? "未知类型"}
          </span>
          <StatusBadge status={asset.status} />
        </div>
        {asset.status === "IN_USE" && currentCheckout && (
          <p className="text-sm text-muted-foreground">
            当前派发给 ·{" "}
            <span className="text-foreground">{currentCheckout.holder}</span>
            {currentCheckout.location ? <> · {currentCheckout.location}</> : null}
            {" · 自 "}
            <time className="font-code">
              {format(parseISO(currentCheckout.checked_out_at), "yyyy-MM-dd HH:mm")}
            </time>
          </p>
        )}
      </div>
      <CtaButton
        status={asset.status}
        onCheckout={onCheckout}
        onReturn={onReturn}
      />
    </header>
  );
}

function CtaButton({
  status,
  onCheckout,
  onReturn,
}: {
  status: AssetRead["status"];
  onCheckout: () => void;
  onReturn: () => void;
}) {
  if (status === "IDLE") {
    return <Button onClick={onCheckout}>{CHECKOUT_VERB}</Button>;
  }
  if (status === "IN_USE") {
    return <Button onClick={onReturn}>{RETURN_VERB}</Button>;
  }
  const reason =
    status === "MAINTENANCE"
      ? "维护中的资产不可派发"
      : "已退役的资产不可派发";
  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          {/* 禁用按钮不触发原生事件，需用 span 包裹才能显示 tooltip */}
          <span tabIndex={0}>
            <Button disabled>{CHECKOUT_VERB}</Button>
          </span>
        </TooltipTrigger>
        <TooltipContent>{reason}</TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}
```

- [ ] **Step 2：接入 `asset-detail-page.tsx`**

```tsx
// frontend/src/features/assets/detail/asset-detail-page.tsx 修改
import { useMemo, useState } from "react";
// ... 原有 imports
import { AssetHeader } from "./asset-header";
import { deriveCurrentCheckout } from "./current-checkout";

export function AssetDetailPage({ id }: AssetDetailPageProps) {
  // 原有 query 调用保留

  const currentCheckout = useMemo(
    () => deriveCurrentCheckout(historyQuery.data),
    [historyQuery.data],
  );
  const typeName = assetType?.name;

  // 占位（Task 16 接线真实 Dialog 打开逻辑）
  const [checkoutOpen, setCheckoutOpen] = useState(false);
  const [returnOpen, setReturnOpen] = useState(false);

  // ... 三态分支保留

  return (
    <>
      <title>{`${asset.name} · asset-hub`}</title>
      <main className="mx-auto max-w-[960px] space-y-10 px-4 py-8">
        <AssetHeader
          asset={asset}
          typeName={typeName}
          currentCheckout={currentCheckout}
          onCheckout={() => setCheckoutOpen(true)}
          onReturn={() => setReturnOpen(true)}
        />
        {/* Task 10-13 填充其他区块 */}
        <div className="text-sm text-muted-foreground">
          其他区块占位
          {checkoutOpen ? " / checkout dialog would open" : ""}
          {returnOpen ? " / return dialog would open" : ""}
        </div>
      </main>
    </>
  );
}
```

- [ ] **Step 3：验证**

```bash
pnpm --dir frontend build && pnpm --dir frontend lint
```

手工：打开详情页，观察：
- Header 名字 + 类型 + StatusBadge 显示正确
- IN_USE 资产下方显示"当前派发给…"
- IDLE → 按钮文字"派发"、IN_USE → "归还"、MAINTENANCE/RETIRED → disabled + hover 显示 tooltip 原因
- 点击按钮后 "checkout dialog would open" / "return dialog would open" 占位文字切换

- [ ] **Step 4：Commit**

```bash
git add frontend/src/features/assets/detail/asset-header.tsx frontend/src/features/assets/detail/asset-detail-page.tsx
git commit -m "feat(frontend): AssetHeader + CtaButton（动词跟随 status + 异常状态 tooltip）"
```

---

## Task 10: `GeneralFields` + Asset ID 复制

**Files:**
- Create: `frontend/src/features/assets/detail/general-fields.tsx`
- Modify: `frontend/src/features/assets/detail/asset-detail-page.tsx`

**§3.5 约束引用：** §3.5.1 fewer-but-better（`<dl>` 语义 + `py-3` 密度）/ §3.5.2（SN / id / 时间戳用 `font-code`）。

- [ ] **Step 1：写 `GeneralFields`**

```tsx
// frontend/src/features/assets/detail/general-fields.tsx
import { useState } from "react";
import { format, parseISO } from "date-fns";
import { Copy, Check } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import type { components } from "@/api/generated/schema";

type AssetRead = components["schemas"]["AssetRead"];

interface GeneralFieldsProps {
  asset: AssetRead;
  typeName: string | undefined;
}

export function GeneralFields({ asset, typeName }: GeneralFieldsProps) {
  return (
    <section>
      <h2 className="mb-3 text-lg font-medium">通用字段</h2>
      <dl className="divide-y divide-border/50">
        <Row label="编号（SN）">
          <span className="font-code">{asset.serial_number ?? "—"}</span>
        </Row>
        <Row label="资产 ID">
          <CopyableId id={asset.id} />
        </Row>
        <Row label="类型">{typeName ?? "—"}</Row>
        <Row label="当前持有人">{asset.holder ?? "—"}</Row>
        <Row label="当前位置">{asset.location ?? "—"}</Row>
        <Row label="备注">
          <span className="whitespace-pre-wrap">{asset.notes ?? "—"}</span>
        </Row>
        <Row label="创建时间">
          <time className="font-code">
            {format(parseISO(asset.created_at), "yyyy-MM-dd HH:mm")}
          </time>
        </Row>
        <Row label="最后更新">
          <time className="font-code">
            {format(parseISO(asset.updated_at), "yyyy-MM-dd HH:mm")}
          </time>
        </Row>
      </dl>
    </section>
  );
}

function Row({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div className="grid grid-cols-[10rem_1fr] gap-4 py-3 text-sm">
      <dt className="text-muted-foreground">{label}</dt>
      <dd>{children}</dd>
    </div>
  );
}

function CopyableId({ id }: { id: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <span className="inline-flex items-center gap-2">
      <span className="font-code">{id}</span>
      <Button
        variant="ghost"
        size="icon"
        className="h-6 w-6"
        aria-label="复制资产 ID"
        onClick={async () => {
          await navigator.clipboard.writeText(id);
          setCopied(true);
          toast.success("资产 ID 已复制");
          setTimeout(() => setCopied(false), 1500);
        }}
      >
        {copied ? (
          <Check className="h-3 w-3" />
        ) : (
          <Copy className="h-3 w-3" />
        )}
      </Button>
    </span>
  );
}
```

- [ ] **Step 2：接入 `asset-detail-page.tsx`**

```tsx
// 在 AssetHeader 下方新增
<GeneralFields asset={asset} typeName={typeName} />
```

记得删除 "其他区块占位" 那行里 GeneralFields 对应的占位。

- [ ] **Step 3：验证**

```bash
pnpm --dir frontend build && pnpm --dir frontend lint
```

手工：浏览器打开详情页，观察：
- 通用字段 8 行整齐显示
- SN / Asset ID / 时间戳用 monospace（Fira Code）
- 点击 Asset ID 右侧"复制"按钮 → Toast "资产 ID 已复制"、图标短暂切换为 Check
- 各字段缺失时显示 "—"（灰色 muted）

- [ ] **Step 4：Commit**

```bash
git add frontend/src/features/assets/detail/general-fields.tsx frontend/src/features/assets/detail/asset-detail-page.tsx
git commit -m "feat(frontend): GeneralFields + Asset ID 复制按钮"
```

---

## Task 11: `CustomFields`

**Files:**
- Create: `frontend/src/features/assets/detail/custom-fields.tsx`
- Modify: `frontend/src/features/assets/detail/asset-detail-page.tsx`

**§3.5 约束引用：** §3.5.1 fewer-but-better / §7.4 spec 空类型字段不渲染整块、未知字段不静默隐藏。

- [ ] **Step 1：写 `CustomFields`**

```tsx
// frontend/src/features/assets/detail/custom-fields.tsx
import {
  formatCustomFieldValue,
  type CustomFieldDef,
} from "./custom-field-formatter";
import type { components } from "@/api/generated/schema";

type AssetRead = components["schemas"]["AssetRead"];
type AssetTypeRead = components["schemas"]["AssetTypeRead"];

interface CustomFieldsProps {
  asset: AssetRead;
  assetType: AssetTypeRead | undefined;
}

export function CustomFields({ asset, assetType }: CustomFieldsProps) {
  // 类型未知（join 失败）或 schema 为空 → 整块不渲染
  const defs = (assetType?.custom_fields ?? []) as CustomFieldDef[];
  const knownKeys = new Set(defs.map((f) => f.key));
  const unknownEntries = Object.entries(asset.custom_data ?? {}).filter(
    ([k]) => !knownKeys.has(k),
  );

  if (defs.length === 0 && unknownEntries.length === 0) return null;

  return (
    <section>
      <h2 className="mb-3 text-lg font-medium">类型字段</h2>
      <dl className="divide-y divide-border/50">
        {defs.map((def) => {
          const data = asset.custom_data as Record<string, unknown> | null;
          const hasValue = data != null && def.key in data;
          return (
            <Row
              key={def.key}
              label={def.label}
              value={
                hasValue ? (
                  formatCustomFieldValue(def, data[def.key])
                ) : (
                  <span className="text-muted-foreground">—</span>
                )
              }
            />
          );
        })}
        {unknownEntries.map(([key, value]) => (
          <Row
            key={key}
            label={
              <span className="italic">
                {key}{" "}
                <small className="text-muted-foreground">（未知字段）</small>
              </span>
            }
            value={String(value)}
          />
        ))}
      </dl>
    </section>
  );
}

function Row({
  label,
  value,
}: {
  label: React.ReactNode;
  value: React.ReactNode;
}) {
  return (
    <div className="grid grid-cols-[10rem_1fr] gap-4 py-3 text-sm">
      <dt className="text-muted-foreground">{label}</dt>
      <dd>{value}</dd>
    </div>
  );
}
```

- [ ] **Step 2：接入 `asset-detail-page.tsx`**

```tsx
// 在 GeneralFields 下方
<CustomFields asset={asset} assetType={assetType} />
```

- [ ] **Step 3：验证**

```bash
pnpm --dir frontend build && pnpm --dir frontend lint
```

手工：
- 有 `custom_fields` 的类型 → 字段按 schema 顺序显示，date 格式化、bool 显示 Check/X icon、int 千分位
- 无 `custom_fields` 的类型 → "类型字段" 整块不渲染
- custom_data 里多了 schema 没有的 key → 显示为 italic + "（未知字段）"

- [ ] **Step 4：Commit**

```bash
git add frontend/src/features/assets/detail/custom-fields.tsx frontend/src/features/assets/detail/asset-detail-page.tsx
git commit -m "feat(frontend): CustomFields——schema-driven 格式化 + 未知字段兜底"
```

---

## Task 12: `CheckoutTimeline`

**Files:**
- Create: `frontend/src/features/assets/detail/checkout-timeline.tsx`
- Modify: `frontend/src/features/assets/detail/asset-detail-page.tsx`

**§3.5 约束引用：** §3.5.3 状态色 / §3.5.5 时刻 2（不做 stagger）/ §3.5.6（节点 / 卡片不用 shadow / 不用 hover 位移）/ §7.6 spec（2 节点形态 + "进行中" 文字标）。

- [ ] **Step 1：写 `CheckoutTimeline`**

```tsx
// frontend/src/features/assets/detail/checkout-timeline.tsx
import { format, parseISO } from "date-fns";
import { EmptyState } from "@/components/feedback/empty-state";
import { ErrorState } from "@/components/feedback/error-state";
import { Skeleton } from "@/components/ui/skeleton";
import type { components } from "@/api/generated/schema";
import type { UseQueryResult } from "@tanstack/react-query";

type CheckoutRead = components["schemas"]["CheckoutRead"];

interface CheckoutTimelineProps {
  query: UseQueryResult<CheckoutRead[]>;
}

export function CheckoutTimeline({ query }: CheckoutTimelineProps) {
  return (
    <section>
      <h2 className="mb-3 text-lg font-medium">流转记录</h2>
      {query.isLoading ? (
        <TimelineSkeleton />
      ) : query.isError ? (
        <ErrorState error={query.error} onRetry={() => query.refetch()} />
      ) : (query.data ?? []).length === 0 ? (
        <EmptyState title="暂无流转记录" description="派发后会在此出现记录。" />
      ) : (
        <ol className="relative pl-6">
          <div
            aria-hidden
            className="absolute left-[7px] top-2 bottom-2 w-px bg-border"
          />
          {(query.data ?? []).map((c) => (
            <li key={c.id} className="relative pb-6 last:pb-0">
              <Node isCurrent={c.returned_at === null} />
              <Card checkout={c} />
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}

function Node({ isCurrent }: { isCurrent: boolean }) {
  return (
    <span
      aria-hidden
      className={
        isCurrent
          ? "absolute left-0 top-1.5 block h-4 w-4 rounded-full bg-[var(--status-active,#16a34a)]"
          : "absolute left-0.5 top-2 block h-3 w-3 rounded-full border-2 border-muted-foreground bg-background"
      }
    />
  );
}

function Card({ checkout: c }: { checkout: CheckoutRead }) {
  const ongoing = c.returned_at === null;
  return (
    <div className="rounded-md ring-1 ring-border/60 p-3 space-y-1">
      <div className="flex items-center justify-between">
        <p className="font-medium">
          {c.holder}
          {c.location ? (
            <span className="ml-2 text-sm text-muted-foreground">
              @ {c.location}
            </span>
          ) : null}
        </p>
        {ongoing && (
          <span className="rounded-sm bg-[var(--status-active,#16a34a)]/10 px-2 py-0.5 text-xs font-medium text-[var(--status-active,#16a34a)]">
            进行中
          </span>
        )}
      </div>
      <p className="font-code text-sm text-muted-foreground">
        {format(parseISO(c.checked_out_at), "yyyy-MM-dd HH:mm")}{" "}
        {ongoing ? (
          <span className="text-muted-foreground">→ —</span>
        ) : (
          <>→ {format(parseISO(c.returned_at!), "yyyy-MM-dd HH:mm")}</>
        )}
      </p>
      {c.checkout_note ? (
        <p className="text-sm text-muted-foreground">
          派发备注：{c.checkout_note}
        </p>
      ) : null}
      {c.return_note && !ongoing ? (
        <p className="text-sm text-muted-foreground">
          归还备注：{c.return_note}
        </p>
      ) : null}
    </div>
  );
}

function TimelineSkeleton() {
  return (
    <div className="relative pl-6 space-y-4">
      {Array.from({ length: 3 }).map((_, i) => (
        <div key={i} className="flex gap-4">
          <Skeleton className="h-3 w-3 rounded-full" />
          <div className="flex-1 space-y-2">
            <Skeleton className="h-4 w-40" />
            <Skeleton className="h-3 w-48" />
          </div>
        </div>
      ))}
    </div>
  );
}
```

- [ ] **Step 2：接入 `asset-detail-page.tsx`**

```tsx
// 在 CustomFields 下方
<CheckoutTimeline query={historyQuery} />
```

- [ ] **Step 3：验证**

```bash
pnpm --dir frontend build && pnpm --dir frontend lint
```

手工：
- 有流转记录时 → 纵向 timeline 显示
- 最上一条 returned_at=null → 实心高亮圆点 + 右上"进行中"小标
- 历史条目 → 空心 muted 圆点
- 无流转 → "暂无流转记录" EmptyState
- history 请求失败 → 区块级 ErrorState，其他区块不受影响

- [ ] **Step 4：Commit**

```bash
git add frontend/src/features/assets/detail/checkout-timeline.tsx frontend/src/features/assets/detail/asset-detail-page.tsx
git commit -m "feat(frontend): CheckoutTimeline——纵向 2 节点形态 + 进行中文字标"
```

---

## Task 13: `AttachmentGrid`（仅缩略图，lightbox 下个 Task）

**Files:**
- Create: `frontend/src/features/assets/detail/attachment-grid.tsx`
- Modify: `frontend/src/features/assets/detail/asset-detail-page.tsx`

**§3.5 约束引用：** §3.5.6 红线（hover 仅 `ring-2 ring-primary/40`，禁 transform scale）/ §7.5 spec。

- [ ] **Step 1：写 `AttachmentGrid`（不含 lightbox）**

```tsx
// frontend/src/features/assets/detail/attachment-grid.tsx
import { Paperclip, FileText, FileImage, File } from "lucide-react";
import { EmptyState } from "@/components/feedback/empty-state";
import { ErrorState } from "@/components/feedback/error-state";
import { Skeleton } from "@/components/ui/skeleton";
import type { components } from "@/api/generated/schema";
import type { UseQueryResult } from "@tanstack/react-query";

type AttachmentRead = components["schemas"]["AttachmentRead"];

interface AttachmentGridProps {
  query: UseQueryResult<AttachmentRead[]>;
  onOpen: (att: AttachmentRead) => void;
}

export function AttachmentGrid({ query, onOpen }: AttachmentGridProps) {
  return (
    <section>
      <h2 className="mb-3 text-lg font-medium">附件</h2>
      {query.isLoading ? (
        <GridSkeleton />
      ) : query.isError ? (
        <ErrorState error={query.error} onRetry={() => query.refetch()} />
      ) : (query.data ?? []).length === 0 ? (
        <EmptyState
          title="暂无附件"
          description="通过登记流程或 asset-hub attachment add CLI 上传。"
        />
      ) : (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
          {(query.data ?? []).map((att) => (
            <button
              key={att.id}
              type="button"
              onClick={() => onOpen(att)}
              className="group relative aspect-square overflow-hidden rounded-md ring-1 ring-border cursor-pointer transition-shadow hover:ring-2 hover:ring-primary/40 focus-visible:ring-2 focus-visible:ring-primary/40"
              aria-label={`查看附件 ${att.original_name}`}
            >
              {att.mime_type.startsWith("image/") ? (
                <img
                  src={`/api/attachments/${att.id}/content`}
                  alt=""
                  loading="lazy"
                  className="h-full w-full object-cover"
                />
              ) : (
                <div className="flex h-full w-full flex-col items-center justify-center gap-2 bg-muted/30 p-2 text-muted-foreground">
                  <KindIcon mime={att.mime_type} />
                  <span className="line-clamp-2 text-xs text-center">
                    {att.original_name}
                  </span>
                </div>
              )}
            </button>
          ))}
        </div>
      )}
    </section>
  );
}

function KindIcon({ mime }: { mime: string }) {
  if (mime === "application/pdf" || mime.includes("document")) {
    return <FileText className="h-6 w-6" aria-hidden />;
  }
  if (mime.startsWith("image/")) {
    return <FileImage className="h-6 w-6" aria-hidden />;
  }
  return <File className="h-6 w-6" aria-hidden />;
}

function GridSkeleton() {
  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
      {Array.from({ length: 4 }).map((_, i) => (
        <Skeleton key={i} className="aspect-square w-full rounded-md" />
      ))}
    </div>
  );
}

// 引用 Paperclip 避免 tree-shake（实际渲染在 EmptyState 内部未用到；保留 import 以备 future）
// eslint-disable-next-line @typescript-eslint/no-unused-vars
const _paperclip = Paperclip;
```

> 注意：`Paperclip` 未使用可删除 import。上面的 `_paperclip` 保险是为了避免 lint 抱怨（若没用到直接删 import 行更简洁）。**实际写代码时：直接去掉 `Paperclip` 的 import**。

- [ ] **Step 2：接入 `asset-detail-page.tsx`**

```tsx
// 顶部引入 useState（已有则复用）
// 浮层相关 state
const [lightboxAttachment, setLightboxAttachment] = useState<
  components["schemas"]["AttachmentRead"] | null
>(null);

// 在 CustomFields 和 CheckoutTimeline 之间插入
<AttachmentGrid
  query={attachmentsQuery}
  onOpen={(att) => setLightboxAttachment(att)}
/>
```

由于 lightbox 还没做，`lightboxAttachment` 点击后只是 state 变化、UI 无反应——Task 14 做 lightbox 后才可见。

- [ ] **Step 3：验证**

```bash
pnpm --dir frontend build && pnpm --dir frontend lint
```

手工：
- 有附件 → 3-4 列宫格（随 viewport）
- 图片 `object-cover` 填满卡片
- 非图 → KindIcon + 文件名文字
- hover → ring 色变（无 scale / shadow）
- 无附件 → EmptyState "暂无附件"

- [ ] **Step 4：Commit**

```bash
git add frontend/src/features/assets/detail/attachment-grid.tsx frontend/src/features/assets/detail/asset-detail-page.tsx
git commit -m "feat(frontend): AttachmentGrid——响应式宫格缩略图 + 图/非图分支"
```

---

## Task 14: `AttachmentLightbox` + 删除 + 接线

**Files:**
- Create: `frontend/src/features/assets/detail/attachment-lightbox.tsx`
- Modify: `frontend/src/features/assets/detail/asset-detail-page.tsx`

**§3.5 约束引用：** §3.4.1 MASTER override（Overlay `bg-black/50` 不 blur）/ §3.5.6 / §7.5 spec。

- [ ] **Step 1：写 `AttachmentLightbox`**

```tsx
// frontend/src/features/assets/detail/attachment-lightbox.tsx
import { useState } from "react";
import { Download, Trash2, X } from "lucide-react";
import { format, parseISO } from "date-fns";
import {
  Dialog,
  DialogContent,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";
import { useDeleteAttachmentMutation } from "@/api/hooks/attachments";
import { toFriendlyMessage } from "@/lib/error";
import { DELETE_ATTACHMENT_PENDING_TEXT } from "./checkout-actions";
import type { components } from "@/api/generated/schema";

type AttachmentRead = components["schemas"]["AttachmentRead"];

interface AttachmentLightboxProps {
  attachment: AttachmentRead | null;
  assetId: string;
  onClose: () => void;
}

export function AttachmentLightbox({
  attachment,
  assetId,
  onClose,
}: AttachmentLightboxProps) {
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [deleteError, setDeleteError] = useState("");
  const deleteMutation = useDeleteAttachmentMutation();

  const open = attachment !== null;

  async function handleDelete() {
    if (!attachment) return;
    setDeleteError("");
    try {
      await deleteMutation.mutateAsync({
        attachmentId: attachment.id,
        assetId,
      });
      setConfirmOpen(false);
      onClose();
    } catch (err) {
      setDeleteError(toFriendlyMessage(err));
    }
  }

  if (!attachment) return null;

  const contentUrl = `/api/attachments/${attachment.id}/content`;
  const isImage = attachment.mime_type.startsWith("image/");

  return (
    <>
      <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
        <DialogContent
          className="max-w-[90vw] max-h-[90vh] p-0 overflow-hidden"
          // Dialog 的默认 DialogTitle 必须存在（a11y）；用 sr-only 隐藏
        >
          <DialogTitle className="sr-only">{attachment.original_name}</DialogTitle>

          {/* 右上角操作栏 */}
          <div className="absolute right-2 top-2 z-10 flex gap-1">
            <Button
              variant="ghost"
              size="icon"
              aria-label="下载附件"
              onClick={() => window.open(contentUrl, "_blank")}
            >
              <Download className="h-4 w-4" />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              aria-label="删除附件"
              onClick={() => setConfirmOpen(true)}
            >
              <Trash2 className="h-4 w-4 text-destructive" />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              aria-label="关闭"
              onClick={onClose}
            >
              <X className="h-4 w-4" />
            </Button>
          </div>

          {isImage ? (
            <img
              src={contentUrl}
              alt={attachment.original_name}
              className="max-h-[90vh] w-auto object-contain"
            />
          ) : (
            <MetadataPanel att={attachment} contentUrl={contentUrl} />
          )}
        </DialogContent>
      </Dialog>

      <AlertDialog open={confirmOpen} onOpenChange={setConfirmOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>确定删除附件？</AlertDialogTitle>
            <AlertDialogDescription>
              删除 <strong>{attachment.original_name}</strong> 后不可恢复。
            </AlertDialogDescription>
          </AlertDialogHeader>
          {deleteError && (
            <p className="text-sm text-destructive">{deleteError}</p>
          )}
          <AlertDialogFooter>
            <AlertDialogCancel disabled={deleteMutation.isPending}>
              取消
            </AlertDialogCancel>
            <AlertDialogAction
              onClick={(e) => {
                e.preventDefault();
                handleDelete();
              }}
              disabled={deleteMutation.isPending}
            >
              {deleteMutation.isPending
                ? DELETE_ATTACHMENT_PENDING_TEXT
                : "确认删除"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}

function MetadataPanel({
  att,
  contentUrl,
}: {
  att: AttachmentRead;
  contentUrl: string;
}) {
  return (
    <div className="flex h-[50vh] flex-col items-center justify-center gap-4 p-10 text-center">
      <div className="space-y-2">
        <h3 className="text-lg font-medium">{att.original_name}</h3>
        <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 text-sm text-muted-foreground">
          <dt>类型</dt>
          <dd className="text-left font-code">{att.mime_type}</dd>
          <dt>大小</dt>
          <dd className="text-left font-code">
            {(att.size / 1024).toFixed(1)} KB
          </dd>
          <dt>上传时间</dt>
          <dd className="text-left font-code">
            {format(parseISO(att.uploaded_at), "yyyy-MM-dd HH:mm")}
          </dd>
        </dl>
      </div>
      <Button onClick={() => window.open(contentUrl, "_blank")}>
        在新窗口打开
      </Button>
    </div>
  );
}
```

- [ ] **Step 2：接入 `asset-detail-page.tsx`**

```tsx
// 页面末尾（main 之外或末尾）
<AttachmentLightbox
  attachment={lightboxAttachment}
  assetId={id}
  onClose={() => setLightboxAttachment(null)}
/>
```

- [ ] **Step 3：验证**

```bash
pnpm --dir frontend build && pnpm --dir frontend lint
```

手工：
- 点击缩略图 → Dialog 打开，图片大图居中 object-contain
- 非图附件点击 → Dialog 内显示 Metadata 面板 + "在新窗口打开"
- overlay 是 `bg-black/50` 半透，**无 blur**
- 右上角 3 个按钮：Download 打开新 tab、Trash 触发 AlertDialog、X 关 Dialog
- AlertDialog 中"确认删除" → DELETE /attachments/:id → Toast + 两个 dialog 都关、Grid 刷新少一项
- 删除时 mock 后端挂掉（kill backend）→ AlertDialog 内 inline error + Toast 不弹

- [ ] **Step 4：§3.5 红线扫描**

```bash
grep -rn "backdrop-blur\|animate-spin\|scale-\|bg-gradient" frontend/src/features/assets/detail/
```

Expected: 0 命中。

- [ ] **Step 5：Commit**

```bash
git add frontend/src/features/assets/detail/attachment-lightbox.tsx frontend/src/features/assets/detail/asset-detail-page.tsx
git commit -m "feat(frontend): AttachmentLightbox——Dialog lightbox + AlertDialog 二次确认删除"
```

---

## Task 15: `CheckoutDialog`

**Files:**
- Create: `frontend/src/features/assets/detail/checkout-dialog.tsx`

**§3.5 约束引用：** §3.4.1 MASTER override（pending 用文字切换不用 spinner）/ §7.7 spec。

- [ ] **Step 1：写 `CheckoutDialog`**

```tsx
// frontend/src/features/assets/detail/checkout-dialog.tsx
import { useEffect, useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useCheckoutMutation } from "@/api/hooks/checkouts";
import { toFriendlyMessage } from "@/lib/error";
import {
  CHECKOUT_DIALOG_TITLE,
  CHECKOUT_PENDING_TEXT,
  CHECKOUT_VERB,
} from "./checkout-actions";

interface CheckoutDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  assetId: string;
}

export function CheckoutDialog({
  open,
  onOpenChange,
  assetId,
}: CheckoutDialogProps) {
  const [holder, setHolder] = useState("");
  const [location, setLocation] = useState("");
  const [note, setNote] = useState("");
  const [holderError, setHolderError] = useState("");
  const [submitError, setSubmitError] = useState("");

  const mutation = useCheckoutMutation();

  useEffect(() => {
    if (!open) {
      setHolder("");
      setLocation("");
      setNote("");
      setHolderError("");
      setSubmitError("");
    }
  }, [open]);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!holder.trim()) {
      setHolderError("请填写保管人");
      return;
    }
    setHolderError("");
    setSubmitError("");
    try {
      await mutation.mutateAsync({
        assetId,
        body: {
          holder: holder.trim(),
          location: location.trim() || null,
          note: note.trim() || null,
        },
      });
      onOpenChange(false);
    } catch (err) {
      setSubmitError(toFriendlyMessage(err));
    }
  }

  return (
    <Dialog
      open={open}
      onOpenChange={(v) => {
        if (!mutation.isPending) onOpenChange(v);
      }}
    >
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{CHECKOUT_DIALOG_TITLE}</DialogTitle>
          <DialogDescription>
            填写保管人后确认，派发记录会自动写入流转历史。
          </DialogDescription>
        </DialogHeader>

        {submitError && (
          <div
            role="alert"
            className="rounded-sm border border-destructive/50 bg-destructive/10 px-3 py-2 text-sm text-destructive"
          >
            {submitError}
          </div>
        )}

        <form onSubmit={onSubmit} className="space-y-4">
          <div className="space-y-1.5">
            <label htmlFor="checkout-holder" className="text-sm font-medium">
              保管人 <span className="text-destructive">*</span>
            </label>
            <Input
              id="checkout-holder"
              value={holder}
              onChange={(e) => setHolder(e.target.value)}
              disabled={mutation.isPending}
              autoFocus
              aria-invalid={holderError ? true : undefined}
              aria-describedby={holderError ? "checkout-holder-err" : undefined}
            />
            {holderError && (
              <p id="checkout-holder-err" className="text-xs text-destructive">
                {holderError}
              </p>
            )}
          </div>

          <div className="space-y-1.5">
            <label htmlFor="checkout-location" className="text-sm font-medium">
              位置（可选）
            </label>
            <Input
              id="checkout-location"
              value={location}
              onChange={(e) => setLocation(e.target.value)}
              disabled={mutation.isPending}
            />
          </div>

          <div className="space-y-1.5">
            <label htmlFor="checkout-note" className="text-sm font-medium">
              备注（可选）
            </label>
            <textarea
              id="checkout-note"
              value={note}
              onChange={(e) => setNote(e.target.value)}
              disabled={mutation.isPending}
              rows={3}
              className="flex w-full rounded-sm border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
            />
          </div>

          <DialogFooter>
            <Button
              type="button"
              variant="ghost"
              onClick={() => onOpenChange(false)}
              disabled={mutation.isPending}
            >
              取消
            </Button>
            <Button type="submit" disabled={mutation.isPending}>
              {mutation.isPending ? CHECKOUT_PENDING_TEXT : `确认${CHECKOUT_VERB}`}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
```

- [ ] **Step 2：验证**

```bash
pnpm --dir frontend build && pnpm --dir frontend lint
```

本 Task Dialog 未接线到 UI，无法手工验证交互——下 Task 接线后一起验。

- [ ] **Step 3：Commit**

```bash
git add frontend/src/features/assets/detail/checkout-dialog.tsx
git commit -m "feat(frontend): CheckoutDialog——纯 React state + 手工校验 + inline error banner"
```

---

## Task 16: `ReturnDialog` + 详情页 CTA 接线

**Files:**
- Create: `frontend/src/features/assets/detail/return-dialog.tsx`
- Modify: `frontend/src/features/assets/detail/asset-detail-page.tsx`

**§3.5 约束引用：** §7.7 spec（顶部展示 currentCheckout 上下文 + data race 保护）。

- [ ] **Step 1：写 `ReturnDialog`**

```tsx
// frontend/src/features/assets/detail/return-dialog.tsx
import { useEffect, useState } from "react";
import { format, parseISO } from "date-fns";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { useReturnMutation } from "@/api/hooks/checkouts";
import { toFriendlyMessage } from "@/lib/error";
import {
  RETURN_DIALOG_TITLE,
  RETURN_PENDING_TEXT,
  RETURN_VERB,
} from "./checkout-actions";
import type { components } from "@/api/generated/schema";

type CheckoutRead = components["schemas"]["CheckoutRead"];

interface ReturnDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  assetId: string;
  currentCheckout: CheckoutRead | null;
}

export function ReturnDialog({
  open,
  onOpenChange,
  assetId,
  currentCheckout,
}: ReturnDialogProps) {
  const [note, setNote] = useState("");
  const [submitError, setSubmitError] = useState("");
  const mutation = useReturnMutation();

  useEffect(() => {
    if (!open) {
      setNote("");
      setSubmitError("");
    }
  }, [open]);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!currentCheckout) return; // data race 保护：按钮 disabled，不应走到这
    setSubmitError("");
    try {
      await mutation.mutateAsync({
        assetId,
        body: { note: note.trim() || null },
      });
      onOpenChange(false);
    } catch (err) {
      setSubmitError(toFriendlyMessage(err));
    }
  }

  return (
    <Dialog
      open={open}
      onOpenChange={(v) => {
        if (!mutation.isPending) onOpenChange(v);
      }}
    >
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{RETURN_DIALOG_TITLE}</DialogTitle>
          <DialogDescription>
            确认归还后会在流转历史中记录归还时间与备注。
          </DialogDescription>
        </DialogHeader>

        {currentCheckout ? (
          <div className="rounded-sm bg-muted/50 px-3 py-2 text-sm">
            当前派发给 · <strong>{currentCheckout.holder}</strong>
            {currentCheckout.location ? <> · {currentCheckout.location}</> : null}
            <br />
            派发于 ·{" "}
            <time className="font-code">
              {format(parseISO(currentCheckout.checked_out_at), "yyyy-MM-dd HH:mm")}
            </time>
          </div>
        ) : (
          <div
            role="alert"
            className="rounded-sm border border-destructive/50 bg-destructive/10 px-3 py-2 text-sm text-destructive"
          >
            此资产当前无派发中记录，请刷新页面。
          </div>
        )}

        {submitError && (
          <div
            role="alert"
            className="rounded-sm border border-destructive/50 bg-destructive/10 px-3 py-2 text-sm text-destructive"
          >
            {submitError}
          </div>
        )}

        <form onSubmit={onSubmit} className="space-y-4">
          <div className="space-y-1.5">
            <label htmlFor="return-note" className="text-sm font-medium">
              备注（可选）
            </label>
            <textarea
              id="return-note"
              value={note}
              onChange={(e) => setNote(e.target.value)}
              disabled={mutation.isPending || !currentCheckout}
              rows={3}
              className="flex w-full rounded-sm border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
            />
          </div>

          <DialogFooter>
            <Button
              type="button"
              variant="ghost"
              onClick={() => onOpenChange(false)}
              disabled={mutation.isPending}
            >
              取消
            </Button>
            <Button
              type="submit"
              disabled={mutation.isPending || !currentCheckout}
            >
              {mutation.isPending ? RETURN_PENDING_TEXT : `确认${RETURN_VERB}`}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
```

- [ ] **Step 2：在 `asset-detail-page.tsx` 接线两个 Dialog**

```tsx
// 顶部 import 增加
import { CheckoutDialog } from "./checkout-dialog";
import { ReturnDialog } from "./return-dialog";

// 已有的 state 保留
// const [checkoutOpen, setCheckoutOpen] = useState(false);
// const [returnOpen, setReturnOpen] = useState(false);

// 返回 JSX 里 </main> 后追加
<CheckoutDialog
  open={checkoutOpen}
  onOpenChange={setCheckoutOpen}
  assetId={id}
/>
<ReturnDialog
  open={returnOpen}
  onOpenChange={setReturnOpen}
  assetId={id}
  currentCheckout={currentCheckout}
/>
```

- [ ] **Step 3：验证**

```bash
pnpm --dir frontend build && pnpm --dir frontend lint
```

手工：
- IDLE 资产点 "派发" → Dialog 开，填 holder 提交 → Toast + Dialog 关 + Header 切 IN_USE + Timeline 多"进行中"
- IDLE 点"派发"不填 holder 提交 → inline red "请填写保管人"
- 提交时 kill 后端 → Dialog 顶部 inline error banner + **Toast 不弹**
- IN_USE 点"归还" → Dialog 开，顶部灰底展示"当前派发给 X"，提交 → Toast + Header 切 IDLE + Timeline 末条填 returned_at
- 归还时 Dialog 保持打开 + mutation pending 时 Dialog 无法 ESC / 外点关

- [ ] **Step 4：Commit**

```bash
git add frontend/src/features/assets/detail/return-dialog.tsx frontend/src/features/assets/detail/asset-detail-page.tsx
git commit -m "feat(frontend): ReturnDialog + CTA 接线——data race 保护 + 当前持有上下文"
```

---

## Task 17: 列表页 RowActions 接线派发/归还

**Files:**
- Modify: `frontend/src/features/assets/list/assets-table.tsx`
- Modify: `frontend/src/routes/index.tsx`

**§3.5 约束引用：** 无新视觉；本 Task 只接线交互。

- [ ] **Step 1：`assets-table.tsx` — `RowActions` 接收 callback，`AssetsTable` props 加两个回调**

```tsx
// frontend/src/features/assets/list/assets-table.tsx 修改

interface AssetsTableProps {
  rows: AssetRow[];
  search: AssetsSearch;
  visible: Record<ColumnKey, boolean>;
  typeNameById: Record<string, string>;
  bodyKey: string;
  onCheckout: (row: AssetRow) => void;   // 新增
  onReturn: (row: AssetRow) => void;     // 新增
}

export function AssetsTable({
  rows,
  search,
  visible,
  typeNameById,
  bodyKey,
  onCheckout,
  onReturn,
}: AssetsTableProps) {
  // ... 内部保留，actions 列的 cell 改为传递 row：
  //   { id: "actions", cell: ({ row }) => (
  //       <RowActions row={row.original} onCheckout={onCheckout} onReturn={onReturn} />
  //     ) }
}

// 改写 RowActions
function RowActions({
  row,
  onCheckout,
  onReturn,
}: {
  row: AssetRow;
  onCheckout: (row: AssetRow) => void;
  onReturn: (row: AssetRow) => void;
}) {
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="icon" aria-label="更多操作" data-asset-id={row.id}>
          <MoreHorizontal className="h-4 w-4" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        <DropdownMenuItem disabled>编辑（M2c-3 开放）</DropdownMenuItem>
        <DropdownMenuItem
          onSelect={() => onCheckout(row)}
          disabled={row.status !== "IDLE"}
        >
          派发
        </DropdownMenuItem>
        <DropdownMenuItem
          onSelect={() => onReturn(row)}
          disabled={row.status !== "IN_USE"}
        >
          归还
        </DropdownMenuItem>
        <DropdownMenuItem disabled>删除（M2c-3 开放）</DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
```

- [ ] **Step 2：`routes/index.tsx` — lift Dialog 状态**

```tsx
// frontend/src/routes/index.tsx 在 AssetListPage 组件内增加：
import { useState } from "react";  // 已有则复用
import { useCheckoutHistoryQuery } from "@/api/hooks/checkouts";
import { deriveCurrentCheckout } from "@/features/assets/detail/current-checkout";
import { CheckoutDialog } from "@/features/assets/detail/checkout-dialog";
import { ReturnDialog } from "@/features/assets/detail/return-dialog";
import type { AssetRow } from "@/features/assets/list/assets-table";

// 在 AssetListPage 函数顶部
const [checkoutRow, setCheckoutRow] = useState<AssetRow | null>(null);
const [returnRow, setReturnRow] = useState<AssetRow | null>(null);

// 归还时需要 currentCheckout 上下文——列表页这里不拉 history，因此 ReturnDialog 开后立即 query
// 方案：在 returnRow 非 null 时挂 history query
const returnHistoryQuery = useCheckoutHistoryQuery(returnRow?.id ?? "");
const currentCheckoutForReturn = deriveCurrentCheckout(
  returnRow ? returnHistoryQuery.data : undefined,
);

// AssetsTable 传 callback：
// <AssetsTable ... onCheckout={(row) => setCheckoutRow(row)}
//                  onReturn={(row) => setReturnRow(row)} />

// 返回 JSX 末尾追加
<CheckoutDialog
  open={!!checkoutRow}
  onOpenChange={(v) => !v && setCheckoutRow(null)}
  assetId={checkoutRow?.id ?? ""}
/>
<ReturnDialog
  open={!!returnRow}
  onOpenChange={(v) => !v && setReturnRow(null)}
  assetId={returnRow?.id ?? ""}
  currentCheckout={currentCheckoutForReturn}
/>
```

> **关键细节**：`useCheckoutHistoryQuery("")` 会对空字符串发请求，导致 404。需要用 `enabled` 选项禁用空 id 的查询——修改 hook：

```ts
// frontend/src/api/hooks/checkouts.ts — useCheckoutHistoryQuery 改：
export function useCheckoutHistoryQuery(assetId: string) {
  return useQuery({
    queryKey: qk.assets.history(assetId),
    queryFn: async () => {
      const res = await http.GET("/api/assets/{asset_id}/history", {
        params: { path: { asset_id: assetId } },
      });
      return unwrap(res);
    },
    enabled: !!assetId,  // 新增：空字符串禁用
  });
}
```

- [ ] **Step 3：验证**

```bash
pnpm --dir frontend build && pnpm --dir frontend lint
```

手工：
- 列表页 IDLE 资产的 ⋯ → "派发" 可点击、"归还" disabled；点"派发" → CheckoutDialog 打开
- IN_USE 资产的 ⋯ → "派发" disabled、"归还" 可点击；点"归还" → ReturnDialog 打开，顶部显示当前持有人（从 history 拉取）
- 提交后 Toast + Dialog 关 + 表格行 status 变（list query 失效触发）
- "编辑 / 删除" 仍 disabled，文案"M2c-3 开放"

- [ ] **Step 4：Commit**

```bash
git add frontend/src/features/assets/list/assets-table.tsx frontend/src/routes/index.tsx frontend/src/api/hooks/checkouts.ts
git commit -m "feat(frontend): 列表页 ⋯ 菜单接线派发/归还——lift Dialog 状态 + enabled 守护空 id"
```

---

## Task 18: 手工烟测 + frontend-design 闸门 ②③ + MASTER 纠偏回写

**Files:**
- Modify: `design-system/asset-hub/MASTER.md`

**§3.5 约束引用：** §3.3 闸门 ② （Task 粒度 review）、③ （合并前最终审查）、④ （纠偏回写）。

- [ ] **Step 1：附录 A 手工烟测 12 项全过**

参考 spec 附录 A 逐项验证。建议开浏览器 + DevTools Network 一起验证：

| # | 步骤 | 通过条件 |
| --- | --- | --- |
| 1 | 列表点行 | `/assets/<uuid>` + 详情显示 |
| 2 | `/assets/not-a-uuid` | NotFoundPanel + "返回列表" |
| 3 | `/assets/<合法不存在 UUID>` | NotFoundPanel |
| 4 | kill 后端 → 详情页刷新 | ErrorState + Retry，起后端点 Retry 成功 |
| 5 | IDLE 资产点派发 → 填 holder 提交 | Dialog 关 + Toast + Header 切 IN_USE + Timeline 多"进行中" |
| 6 | IN_USE 资产点归还 → 提交 | Dialog 关 + Toast + Header 切 IDLE + Timeline 末条 returned_at 填上 |
| 7 | 派发 Dialog 不填 holder 提交 | inline error "请填写保管人"；按钮不进 pending |
| 8 | 派发 Dialog 提交时 kill 后端 | Dialog 保持打开 + 顶部 inline ErrorBanner + **Toast 不弹** |
| 9 | MAINTENANCE/RETIRED 资产 | CTA disabled + hover tooltip |
| 10 | 附件点缩略图 | Lightbox 开；图 → contain；非图 → metadata panel |
| 11 | Lightbox 点删除 → AlertDialog 确认 → 确认 | Toast + 两 Dialog 关 + 网格刷新 |
| 12 | 切 Light/Dark/System | 无闪烁、状态色正确、timeline 节点随主题翻转 |

- [ ] **Step 2：§3.5 红线扫描（grep）**

```bash
grep -rn "scale-\|animate-spin\|backdrop-blur\|bg-gradient\|gradient" \
  frontend/src/features/assets/detail/ \
  frontend/src/api/hooks/checkouts.ts \
  frontend/src/api/hooks/attachments.ts \
  frontend/src/routes/assets.\$id.tsx \
  frontend/src/components/ui/dialog.tsx \
  frontend/src/components/ui/alert-dialog.tsx
```

Expected: 0 命中。如有命中立即修复。

- [ ] **Step 3：MASTER `Pre-Delivery Checklist` 7 项逐项打勾**

参考 `design-system/asset-hub/MASTER.md` 末尾 Pre-Delivery Checklist 7 项，逐一确认：
- No emojis as icons ✓（全 Lucide）
- cursor-pointer on clickable（Button 自带 + 缩略图 button）
- Hover transitions 150-300ms（`transition-colors` / `transition-shadow`）
- Light mode text contrast 4.5:1（状态色、dl 的 muted-foreground / foreground 对比已满足）
- Focus states visible（globals.css `*:focus-visible` + Dialog 的 `focus-visible:ring-2`）
- `prefers-reduced-motion` respected（globals.css 媒体查询降级）
- Responsive 1024+（max-width 960，<1024 附件宫格自动降列）

- [ ] **Step 4：MASTER 末尾追加"实施期纠偏（M2c-2）"区块**

打开 `design-system/asset-hub/MASTER.md`，在文件末尾追加：

````markdown
---

## 实施期纠偏（M2c-2，2026-04-25）

`frontend-design` skill 合并前审查 + 手工烟测（spec 附录 A 12 项）+ Pre-Delivery Checklist 7 项全部通过后回写。M2c-1 纠偏项（后端 `asset_code` / `type_name` 缺口）仍保留；以下是 M2c-2 新增的记录。

### 1. MASTER 显式 override 清单（兑现 spec §3.4.1）

本里程碑对 MASTER 做了以下覆盖，理由已在 spec §3.4.1 记录：

- **`Key Effects: data loading spinners` → 改用按钮文字切换 + 骨架**（spinner 是 AI-slop 重灾区）
- **`Modal backdrop-filter: blur(4px)` → 改 `bg-black/50` 不 blur**（glassmorphism 是 overused AI 审美）
- **`Card: box-shadow + hover translateY` → 详情页不用 Card 装饰**（fewer-but-better；hover 位移与 MASTER 自己的 anti-pattern #3 矛盾）
- **`<Separator>` 未使用**（spec §7.1 决定 space-y-10 + `<h2>` 语义分区即可）

### 2. Timeline 视觉当前保留最简 2 节点形态

本里程碑 timeline 节点视觉只区分「当前派发 = 实心高亮圆点 + 进行中文字标 / 历史 = 空心 muted 圆点」。M3 候选增强清单见 spec §10.2：
- 时间近远渐隐（opacity 分级 ≤90d / ≤180d / 更早）
- 派出类型染色（与派出类型扩展联动）
- 超长派发预警（> 90 天未归还，节点加 `Clock` + 警示色）

M3 启动时按此清单重构，不要重新讨论。

### 3. Dialog 表单用纯 React state

M2c-2 两个 Dialog（`CheckoutDialog` / `ReturnDialog`）用 `useState` + 手工校验实现，未引入 RHF+Zod。M2c-3 引入 Vitest + RHF + Zod 时，将把这两个 Dialog 迁到 RHF 版本（约半天工作量）。迁移只改表单状态 + 校验层，不动 JSX 骨架 / Toast / mutation hook。

已在 M2c-3 plan（尚未起草）起笔时要求列为独立 Task，避免遗漏。

### 4. `useCheckoutHistoryQuery` 的 `enabled` 守护

列表页 ⋯ 菜单的 `ReturnDialog` 在 `returnRow === null` 时传 `assetId=""`。最初实现会对空字符串发 `/api/assets//history` 请求（404）。Task 17 已修：hook 加 `enabled: !!assetId`。

后续若新增更多"条件拉取"类的 query，遵循此模式。

### 5. `useDeleteAttachmentMutation` 不走 `unwrap`

DELETE 端点返回 204 无 body，`unwrap` 要求 `data` 存在会抛错。hook 内手工处理 `res.error` 即可，不改 `unwrap` 签名。

若后续新增更多 204 端点，可考虑给 `unwrap` 加一个 `allowEmpty` 选项；但单例不值当。

### Pre-Delivery Checklist（M2c-2 验证）

- [x] No emojis as icons（全 Lucide SVG：SearchX / Copy / Check / X / Download / Trash2 / FileText / FileImage / File / Paperclip 等）
- [x] cursor-pointer on clickable elements（shadcn Button 默认；缩略图 button 显式 `cursor-pointer`）
- [x] Hover transitions smooth 150-300ms（`transition-colors` / `transition-shadow`；无 `transform: scale`）
- [x] Light mode text contrast 4.5:1（muted-foreground on background 实测 ≈ 5:1；destructive text 实测 ≈ 6.5:1）
- [x] Focus states visible for keyboard（globals.css `*:focus-visible` 兜底；Dialog / AlertDialog 默认 focus trap）
- [x] `prefers-reduced-motion` respected（globals.css 媒体查询降级已继承；Radix Dialog 的 scale-in 默认尊重 reduced-motion）
- [x] Responsive 1024+（max-width 960；<1024 附件宫格自动从 4 列降至 3/2 列）

手工烟测通过项（spec 附录 A）：逐项打勾并在此补标日期。
````

- [ ] **Step 5：`pnpm build` / `pnpm lint` 全绿 + 提交纠偏**

```bash
pnpm --dir frontend build && pnpm --dir frontend lint
git add design-system/asset-hub/MASTER.md
git commit -m "chore(m2c2): M2c-2 最终审查与纠偏回写——frontend-design 合并前闸门通过"
```

- [ ] **Step 6：（可选）合并到 main**

如果整条开发都在 `feature/m2c2-frontend` 分支，走 PR + squash-merge 或 fast-forward merge；若直接在 main 上做则本步可跳过。

---

## 实施期纠偏（M2c-2）

与 M2c-1 plan 同款占位：实施期发现的上游缺口、临时权宜、偏离 MASTER 的细节，由 Task 18 Step 4 回写到 `design-system/asset-hub/MASTER.md`。本 plan 不在此节展开（避免 plan 与 MASTER 双源）。

---

## 自检清单（写完 plan 的最后一步）

本节仅作者阅读；执行者无需勾选。

### 1. Spec 覆盖

| spec 节点 | 对应 Task |
| --- | --- |
| §1 目标 In-scope 全部项 | 全部 Task |
| §2 关键决策 D1-D8 | 贯穿（D1 纯只读 → Task 2 hook 不含 update；D2 单列 → Task 8 布局；D3 纯前端推导 → Task 4 deriveCurrentCheckout；D4 CTA 动词 → Task 9；D5 timeline → Task 12；D6 lightbox → Task 14；D7 schema formatter → Task 4 + Task 11；D8 纯 React state → Task 15/16） |
| §3.1-§3.2 baseline 继承 / 不生成 page override | 无单独 Task，继承 M2c-1 |
| §3.3 闸门 ①②③④ | 闸门 ①（spec 阶段 frontend-design review） 已在 spec commit 前完成；闸门 ② 每 UI Task 末尾 §3.5 约束栏；闸门 ③④ Task 18 |
| §3.4 审美纲领 | Task 9-16 每任务的 §3.5 约束引用栏 |
| §3.4.1 MASTER override | Task 3（Dialog overlay）、Task 12（timeline 无 shadow）、Task 18 Step 4 回写 |
| §4.1 架构 | 全部 Task 构成 |
| §4.2 文件结构 | 14 个新文件 + 4 个修改文件 全部对应到 Task |
| §4.3 依赖（无新增 npm） | Task 3（仅 shadcn add） |
| §5.1 queryKey | Task 1 |
| §5.2 hooks 一览 | Task 1 + Task 2 |
| §5.3 mutation 失效 | Task 2 onSuccess invalidate |
| §5.4 当前派发派生 | Task 4 |
| §5.5 并发模式 | Task 8（3 query 并发）+ Task 12（各区块独立 loading/error） |
| §6 路由 + UUID 校验 | Task 8 |
| §7.1 三态壳 | Task 8 |
| §7.2 AssetHeader + CtaButton | Task 9 |
| §7.3 GeneralFields | Task 10 |
| §7.4 CustomFields + formatter | Task 4 + Task 11 |
| §7.5 AttachmentGrid + Lightbox | Task 13 + Task 14 |
| §7.6 CheckoutTimeline | Task 12 |
| §7.7 CheckoutDialog / ReturnDialog | Task 15 + Task 16 |
| §7.8 NotFoundPanel | Task 6 |
| §7.9 列表页接通 | Task 17 |
| §8 错误处理 4 层 | Task 8（route parseParams/404/error）+ Task 12/13（区块 ErrorState）+ Task 15/16（Dialog inline banner） |
| §9 不引入 Vitest | 每 Task 验证用 `pnpm build` + `pnpm lint` + 手工 |
| §10 扩展兼容性 M3 | Task 5 checkout-actions.ts（派出类型扩展锚）+ Task 18 MASTER 纠偏回写（timeline 重构 + 迁 RHF 备忘） |
| §11 DoD | Task 18 |
| 附录 A 手工烟测 12 项 | Task 18 Step 1 |

### 2. Placeholder 扫描

grep `TBD|TODO|implement later|FIXME` ——本 plan 无匹配 ✓（Task 9 中的 `setTimeout` 是真实代码不是占位）。

### 3. 类型一致

- `components["schemas"]["AssetRead"]` / `CheckoutRead` / `AttachmentRead` / `AssetTypeRead` 均直接从 openapi-typescript 生成取，Task 9/10/11/12/13/14/15/16 引用方式一致 ✓
- `AssetRow` 从 `features/assets/list/assets-table` 导出，Task 17 在 `routes/index.tsx` 引用 ✓
- `deriveCurrentCheckout` 签名 `(history: CheckoutRead[] | undefined) => CheckoutRead | null`，Task 9/16/17 调用一致 ✓
- `useCheckoutMutation` / `useReturnMutation` mutationFn 入参均 `{ assetId, body }`，Task 15/16 一致 ✓
- `useDeleteAttachmentMutation` mutationFn 入参 `{ attachmentId, assetId }`，Task 14 使用一致 ✓
- `CHECKOUT_VERB / RETURN_VERB / CHECKOUT_DIALOG_TITLE / RETURN_DIALOG_TITLE / CHECKOUT_PENDING_TEXT / RETURN_PENDING_TEXT / DELETE_ATTACHMENT_PENDING_TEXT` 从 `checkout-actions.ts` 导出，Task 9/14/15/16 import 一致 ✓

### 4. frontend-design 隐性 shadcn 默认扫描（spec §3.3 ② 要求）

- Dialog / AlertDialog overlay 的 `bg-black/80` 默认改为 `bg-black/50` — Task 3 Step 2 明确 ✓
- 无 `shadcn Card` 的使用 — Task 9-16 均未用 Card ✓
- AttachmentLightbox Dialog header 用自绘 header（sr-only DialogTitle + 浮动按钮），不走 DialogHeader 默认样式避免 `text-lg font-semibold` 的 MASTER 字重差异 ✓
- 所有 `rounded-*` 通过 `--radius=0.375rem` 自动跟（M2c-1 已生效） ✓
- 无渐变背景、无 backdrop-blur、无 hover transform（Task 14 Step 4 扫描 ✓，Task 18 Step 2 再扫） ✓

---

**Plan complete and saved to `docs/superpowers/plans/2026-04-25-m2c2-detail-flow-attachments.md`. Two execution options:**

**1. Subagent-Driven (recommended)** - 我派发 fresh subagent 逐 Task 实施，Task 间可 review，迭代快

**2. Inline Execution** - 在当前会话里执行，批量带 checkpoints

**Which approach?**
