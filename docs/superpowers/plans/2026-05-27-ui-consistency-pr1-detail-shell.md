# PR-1：DetailPageShell 抽取 + 类型详情对齐资产 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 抽出共享详情页骨架 `<DetailPageShell>`，资产详情改用它（视觉不变），类型详情拆成「只读视图 + 独立编辑页」完全对齐资产架构。

**Architecture:** 新增纯展示组件 `DetailPageShell`（居中窄栏 + 返回链接 slot + 标题/meta/actions slot + children）。资产详情把现有 header 结构搬进 shell。类型新增只读视图（镜像资产 `general-fields` 的 dl 行 + custom_fields schema 只读区）走 shell；类型编辑表单移到新路由 `/types/$id/edit`；`/types/$id` 路由改渲染只读视图。纯前端，无后端/schema 改动（`ref_count` / `custom_fields` 已在 `TypeRead`）。

**Tech Stack:** React 19 + TanStack Router（file-based）+ TanStack Query + vitest + Testing Library。决策依据见 `docs/superpowers/specs/2026-05-26-ui-consistency-batch-design.md` §视觉决策 决策 1/2/3。

---

## File Structure

- **Create** `frontend/src/components/layout/detail-page-shell.tsx` — 共享详情页骨架（纯展示，slot 驱动）
- **Create** `frontend/tests/components/detail-page-shell.test.tsx` — shell 单测
- **Modify** `frontend/src/features/assets/detail/asset-header.tsx` — 导出 `AssetActionArea`；拆出 title/meta 供 shell slot
- **Modify** `frontend/src/features/assets/detail/asset-detail-page.tsx` — 改用 `DetailPageShell`
- **Modify** `frontend/tests/components/asset-header.test.tsx` — 适配重构（测 `AssetActionArea`）
- **Create** `frontend/src/features/types/detail/type-custom-fields-display.tsx` — 只读 custom_fields schema 展示
- **Create** `frontend/src/features/types/detail/type-detail-view.tsx` — 类型只读视图（用 shell）
- **Create** `frontend/tests/components/type-detail-view.test.tsx` — 只读视图单测
- **Create** `frontend/src/routes/types.$id.edit.tsx` — 类型编辑路由
- **Modify** `frontend/src/routes/types.$id.tsx` — 转为 Outlet 布局层（镜像 `assets.$id.tsx`：`parseParams` uuid + `errorComponent`）
- **Create** `frontend/src/routes/types.$id.index.tsx` — 类型只读详情路由（渲染 `TypeDetailView`）
- **Delete** `frontend/src/features/types/detail/type-detail-page.tsx` — 旧合并页（拆解后删除）
- **Delete** `frontend/src/features/types/detail/type-summary-card.tsx` — 元信息并入只读视图后删除

无后端改动 → **不跑 `gen:api`**，无 alembic。

---

## Task 1: DetailPageShell 共享骨架

**Files:**
- Create: `frontend/src/components/layout/detail-page-shell.tsx`
- Test: `frontend/tests/components/detail-page-shell.test.tsx`

- [ ] **Step 1: 写失败测试**

```tsx
// frontend/tests/components/detail-page-shell.test.tsx
import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import { DetailPageShell } from "@/components/layout/detail-page-shell";

describe("DetailPageShell", () => {
  it("渲染返回链接 / 标题 / actions / children 四个 slot", () => {
    render(
      <DetailPageShell
        backLink={<a href="/back">← 返回</a>}
        title="测试标题"
        actions={<button>编辑</button>}
      >
        <p>正文区</p>
      </DetailPageShell>,
    );
    expect(screen.getByRole("link", { name: "← 返回" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "测试标题" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "编辑" })).toBeInTheDocument();
    expect(screen.getByText("正文区")).toBeInTheDocument();
  });

  it("title 用 h1.text-2xl；titleAccessory 与 meta 可选渲染", () => {
    render(
      <DetailPageShell
        backLink={<span>back</span>}
        title="标题"
        titleAccessory={<span>角标</span>}
        meta={<span>元信息行</span>}
      >
        <p>x</p>
      </DetailPageShell>,
    );
    const h1 = screen.getByRole("heading", { name: "标题" });
    expect(h1.className).toContain("text-2xl");
    expect(screen.getByText("角标")).toBeInTheDocument();
    expect(screen.getByText("元信息行")).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: 跑测试确认失败**

Run: `pnpm --dir frontend exec vitest run tests/components/detail-page-shell.test.tsx`
Expected: FAIL（`Cannot find module '@/components/layout/detail-page-shell'`）

- [ ] **Step 3: 写实现**

```tsx
// frontend/src/components/layout/detail-page-shell.tsx
import type { ReactNode } from "react";

interface DetailPageShellProps {
  /** 返回链接 slot（页面提供 typed <Link>，沿用 NotFoundPanel 的 backLink slot 模式）。 */
  backLink: ReactNode;
  /** 主标题文本（置于 h1.text-2xl，详情档 type scale）。 */
  title: ReactNode;
  /** 标题旁配饰（如逾期角标），可选。 */
  titleAccessory?: ReactNode;
  /** 标题下方元信息行，可选。 */
  meta?: ReactNode;
  /** 右侧操作区，可选。 */
  actions?: ReactNode;
  children: ReactNode;
}

/** 资产 / 类型详情页共享骨架：居中 960 窄栏 + 返回 + 标题/meta/actions + 正文。 */
export function DetailPageShell({
  backLink,
  title,
  titleAccessory,
  meta,
  actions,
  children,
}: DetailPageShellProps) {
  return (
    <main className="mx-auto max-w-[960px] space-y-10 px-4 py-8">
      <header className="flex items-start justify-between gap-4">
        <div className="space-y-1">
          {backLink}
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-semibold">{title}</h1>
            {titleAccessory}
          </div>
          {meta}
        </div>
        {actions}
      </header>
      {children}
    </main>
  );
}
```

- [ ] **Step 4: 跑测试确认通过**

Run: `pnpm --dir frontend exec vitest run tests/components/detail-page-shell.test.tsx`
Expected: PASS（2 通过）

- [ ] **Step 5: 提交**

```bash
git add frontend/src/components/layout/detail-page-shell.tsx frontend/tests/components/detail-page-shell.test.tsx
git commit -m "feat(frontend): 抽 DetailPageShell 详情页共享骨架"
```

---

## Task 2: 资产详情改用 DetailPageShell（视觉不变）

**Files:**
- Modify: `frontend/src/features/assets/detail/asset-header.tsx`
- Modify: `frontend/src/features/assets/detail/asset-detail-page.tsx:58-78`
- Modify: `frontend/tests/components/asset-header.test.tsx`

目标：把 `asset-header.tsx` 里的 `<header>` 外壳拆掉，导出 `AssetActionArea`（原 `ActionArea`，含所有 transition dialog，零逻辑改动），并导出构建 title/meta 的小组件；`asset-detail-page` 用 `DetailPageShell` 组合。**最终 DOM 与现状一致**（shell 复刻了原 header 的 `flex items-start justify-between` + 左列 `space-y-1`）。

- [ ] **Step 1: 改 asset-header.tsx —— 拆外壳、导出 ActionArea 与 title/meta**

把 `asset-header.tsx` 整体替换为（`ActionArea` 改名 `AssetActionArea` 并 `export`；新增导出 `AssetTitleAccessory`（逾期角标）与 `AssetMeta`（元信息行）；删除原 `AssetHeader` 的 `<header>` 外壳，保留 hook）：

```tsx
import { Link, useNavigate } from "@tanstack/react-router";
import { Clock, MoreHorizontal } from "lucide-react";
import { useState } from "react";

import { useTransitionsQuery } from "@/api/hooks/transitions";
import type { AssetRead, TransitionKind } from "@/features/assets/types";
import { StatusBadge } from "@/components/status/status-badge";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { calcOverdue } from "@/lib/overdue";
import { findOpenCheckout } from "@/lib/transition-state";
import { cn } from "@/lib/utils";

import { MENU_ACTIONS, PRIMARY_ACTIONS } from "./available-transitions";
import { CheckoutDialog } from "./checkout-dialog";
import { DeclareUnrepairableAlertDialog } from "./declare-unrepairable-alert-dialog";
import { DisposeAlertDialog } from "./dispose-alert-dialog";
import { ReassignDialog } from "./reassign-dialog";
import { RetireAlertDialog } from "./retire-alert-dialog";
import { ReturnDialog } from "./return-dialog";
import { SimpleTransitionDialog } from "./simple-transition-dialog";

export function useOverdueForOpenCheckout(
  assetId: string,
  assetStatus: AssetRead["status"],
) {
  const { data: transitions } = useTransitionsQuery(assetId);
  if (!transitions) return null;
  const open = findOpenCheckout(transitions);
  if (!open) return null;
  return calcOverdue(open.due_at, assetStatus);
}

/** 资产详情标题旁的逾期角标（DetailPageShell titleAccessory slot）。 */
export function AssetTitleAccessory({ asset }: { asset: AssetRead }) {
  const overdue = useOverdueForOpenCheckout(asset.id, asset.status);
  if (!overdue || overdue.status === "pending") return null;
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium",
        overdue.status === "due-soon" && "bg-warning/15 text-warning-fg",
        overdue.status === "overdue" && "bg-destructive/15 text-destructive",
      )}
    >
      <Clock className="size-3" aria-hidden />
      {overdue.status === "due-soon"
        ? `还有 ${overdue.days} 天到期`
        : `逾期 ${overdue.days} 天`}
    </span>
  );
}

/** 资产详情元信息行（DetailPageShell meta slot）。 */
export function AssetMeta({ asset }: { asset: AssetRead }) {
  return (
    <>
      <div className="flex items-center gap-3">
        <span className="font-code text-sm text-muted-foreground">
          {asset.asset_code}
        </span>
        <span className="text-sm text-muted-foreground">·</span>
        <span className="text-sm text-muted-foreground">
          {asset.type_name ?? "未知类型"}
        </span>
        {(asset.brand || asset.model) && (
          <>
            <span className="text-sm text-muted-foreground">·</span>
            <span className="text-sm text-muted-foreground">
              {[asset.brand, asset.model].filter(Boolean).join(" · ")}
            </span>
          </>
        )}
        <StatusBadge status={asset.status} />
      </div>
      {asset.holder && (
        <p className="text-sm text-muted-foreground">
          当前保管人 ·{" "}
          <span className="text-foreground">{asset.holder}</span>
          {asset.location ? <> · {asset.location}</> : null}
        </p>
      )}
    </>
  );
}

export function AssetActionArea({
  asset,
  onDelete,
}: {
  asset: AssetRead;
  onDelete: () => void;
}) {
  const navigate = useNavigate();
  const status = asset.status;
  const primaries = PRIMARY_ACTIONS[status];
  const menuItems = MENU_ACTIONS[status];
  const [openDialog, setOpenDialog] = useState<TransitionKind | null>(null);

  const isReadonly = status === "DISPOSED";
  const closeDialog = (open: boolean) => !open && setOpenDialog(null);

  return (
    <div className="flex items-center gap-2">
      {primaries.map((p) => (
        <Button key={p.kind} onClick={() => setOpenDialog(p.kind)}>
          {p.label}
        </Button>
      ))}

      {!isReadonly && (
        <Button
          variant="outline"
          onClick={() =>
            navigate({ to: "/assets/$id/edit", params: { id: asset.id } })
          }
        >
          编辑
        </Button>
      )}

      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="ghost" size="icon" aria-label="更多操作">
            <MoreHorizontal className="h-4 w-4" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end">
          {menuItems.map((action) => (
            <DropdownMenuItem
              key={action.kind}
              onSelect={() => setOpenDialog(action.kind)}
            >
              {action.label}…
            </DropdownMenuItem>
          ))}

          {menuItems.length > 0 && <DropdownMenuSeparator />}

          {status === "IN_USE" ? (
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <span tabIndex={0}>
                    <DropdownMenuItem disabled className="text-destructive">
                      删除
                    </DropdownMenuItem>
                  </span>
                </TooltipTrigger>
                <TooltipContent>需先归还</TooltipContent>
              </Tooltip>
            </TooltipProvider>
          ) : (
            <DropdownMenuItem
              onSelect={onDelete}
              className="text-destructive focus:text-destructive"
            >
              删除…
            </DropdownMenuItem>
          )}
        </DropdownMenuContent>
      </DropdownMenu>

      {(openDialog === "CHECKOUT_INTERNAL" || openDialog === "CHECKOUT_EXTERNAL") && (
        <CheckoutDialog open onOpenChange={closeDialog} assetId={asset.id} kind={openDialog} />
      )}
      {openDialog === "RETURN" && (
        <ReturnDialog open onOpenChange={closeDialog} assetId={asset.id} />
      )}
      {(openDialog === "SEND_TO_MAINTENANCE" ||
        openDialog === "RECOVER_FROM_MAINTENANCE" ||
        openDialog === "REINSTATE" ||
        openDialog === "REPORT_BROKEN" ||
        openDialog === "DISMISS") && (
        <SimpleTransitionDialog
          open
          onOpenChange={closeDialog}
          assetId={asset.id}
          kind={openDialog}
          currentHolder={asset.holder ?? null}
          currentLocation={asset.location ?? null}
        />
      )}
      {openDialog === "RETIRE" && (
        <RetireAlertDialog open onOpenChange={closeDialog} assetId={asset.id} assetName={asset.name} />
      )}
      {openDialog === "DISPOSE" && (
        <DisposeAlertDialog open onOpenChange={closeDialog} assetId={asset.id} assetName={asset.name} />
      )}
      {openDialog === "DECLARE_UNREPAIRABLE" && (
        <DeclareUnrepairableAlertDialog
          open
          onOpenChange={closeDialog}
          assetId={asset.id}
          assetName={asset.name}
        />
      )}
      {openDialog === "REASSIGN" && (
        <ReassignDialog
          open
          onOpenChange={closeDialog}
          assetId={asset.id}
          currentHolder={asset.holder ?? null}
          currentLocation={asset.location ?? null}
        />
      )}
    </div>
  );
}
```

（注意：`Link` import 保留——`asset-detail-page` 会用；若 lint 报 `Link` 未用可在本文件删除该 import，由 `asset-detail-page` 自带。实施时按实际 lint 结果处理。）

- [ ] **Step 2: 改 asset-detail-page.tsx 用 DetailPageShell**

把 `asset-detail-page.tsx` 的 import 段与 return 段改为：

import 段把 `import { AssetHeader } from "./asset-header";` 换成：

```tsx
import { Link } from "@tanstack/react-router";
import { DetailPageShell } from "@/components/layout/detail-page-shell";
import { AssetActionArea, AssetMeta, AssetTitleAccessory } from "./asset-header";
```

return 段（原 58-78 行的 `<main>...<AssetHeader/>...</main>`）替换为：

```tsx
  return (
    <>
      <title>{`${asset.name} · asset-hub`}</title>
      <DetailPageShell
        backLink={
          <Link
            to="/"
            search={{ sort: "asset_code", page: 1, pageSize: 50 }}
            className="text-sm text-muted-foreground hover:text-foreground transition-colors"
          >
            ← 返回列表
          </Link>
        }
        title={asset.name}
        titleAccessory={<AssetTitleAccessory asset={asset} />}
        meta={<AssetMeta asset={asset} />}
        actions={<AssetActionArea asset={asset} onDelete={() => setDeleteOpen(true)} />}
      >
        <GeneralFields asset={asset} typeName={typeName} />
        <CustomDataSection
          customData={(asset.custom_data ?? {}) as Record<string, unknown>}
          fieldDefs={(assetType?.custom_fields ?? []) as FieldDef[]}
          assetId={asset.id}
        />
        <AttachmentGrid
          query={attachmentsQuery}
          onOpen={(att) => setLightboxAttachment(att)}
          assetId={asset.id}
        />
        <TransitionTimeline assetId={asset.id} assetStatus={asset.status} />
      </DetailPageShell>
      <AttachmentLightbox
        attachment={lightboxAttachment}
        assetId={id}
        onClose={() => setLightboxAttachment(null)}
      />
      <DeleteAssetAlert
        open={deleteOpen}
        onOpenChange={setDeleteOpen}
        asset={{ id: asset.id, name: asset.name, asset_code: asset.asset_code }}
        onDeleted={() =>
          navigate({
            to: "/",
            search: { sort: "asset_code", page: 1, pageSize: 50 },
          })
        }
      />
    </>
  );
```

- [ ] **Step 3: 改 asset-header.test.tsx 适配重构**

旧测试 import `AssetHeader` 并断言逾期角标。改为测 `AssetActionArea`（行为核心）+ `AssetTitleAccessory`（角标）。把文件中 `import { AssetHeader } ...` 改为 `import { AssetActionArea, AssetTitleAccessory } from "@/features/assets/detail/asset-header";`，并把渲染 `<AssetHeader asset={...} onDelete={...} />` 的用例改为对应组件。原"逾期 N 天 / 还有 N 天到期"断言移到渲染 `<AssetTitleAccessory asset={...} />` 的用例（`renderWithProviders` 不变，因为 hook 用 `useTransitionsQuery` + 需 mock）。原校验主操作按钮/菜单的用例改渲染 `<AssetActionArea asset={...} onDelete={vi.fn()} />`。

具体：把每处 `renderWithProviders(<AssetHeader asset={asset} onDelete={onDelete} />)` 替换为 `renderWithProviders(<AssetActionArea asset={asset} onDelete={onDelete} />)`；逾期角标相关用例替换为 `renderWithProviders(<AssetTitleAccessory asset={asset} />)`（角标用例 `onDelete` 不需要）。

- [ ] **Step 4: 跑测试 + 类型校验**

Run: `pnpm --dir frontend exec vitest run tests/components/asset-header.test.tsx tests/components/detail-page-shell.test.tsx`
Expected: PASS
Run: `pnpm --dir frontend exec tsc -b`
Expected: 无错误

- [ ] **Step 5: 提交**

```bash
git add frontend/src/features/assets/detail/asset-header.tsx frontend/src/features/assets/detail/asset-detail-page.tsx frontend/tests/components/asset-header.test.tsx
git commit -m "refactor(frontend): 资产详情改用 DetailPageShell，导出 AssetActionArea/AssetMeta/AssetTitleAccessory"
```

---

## Task 3: 只读 custom_fields schema 展示组件

**Files:**
- Create: `frontend/src/features/types/detail/type-custom-fields-display.tsx`
- Test: `frontend/tests/unit/type-custom-fields-display.test.tsx`

类型只读视图需要把 `custom_fields` schema（每项 key/label/type/required/options）只读列出。

- [ ] **Step 1: 写失败测试**

```tsx
// frontend/tests/unit/type-custom-fields-display.test.tsx
import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import { TypeCustomFieldsDisplay } from "@/features/types/detail/type-custom-fields-display";
import type { TypeRead } from "@/features/assets/types";

type Field = TypeRead["custom_fields"][number];

const fields = [
  { key: "cpu", label: "处理器", type: "string", required: true } as Field,
  {
    key: "tier",
    label: "档位",
    type: "enum",
    required: false,
    options: ["低", "高"],
  } as Field,
];

describe("TypeCustomFieldsDisplay", () => {
  it("列出每个字段的 label / key / 类型，必填标记，enum 选项", () => {
    render(<TypeCustomFieldsDisplay fields={fields} />);
    expect(screen.getByText("处理器")).toBeInTheDocument();
    expect(screen.getByText("cpu")).toBeInTheDocument();
    expect(screen.getByText("档位")).toBeInTheDocument();
    expect(screen.getByText(/低.*高|低、高/)).toBeInTheDocument();
    expect(screen.getByText("必填")).toBeInTheDocument();
  });

  it("空字段列表显示占位", () => {
    render(<TypeCustomFieldsDisplay fields={[]} />);
    expect(screen.getByText("无自定义字段")).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: 跑测试确认失败**

Run: `pnpm --dir frontend exec vitest run tests/unit/type-custom-fields-display.test.tsx`
Expected: FAIL（模块不存在）

- [ ] **Step 3: 写实现**

```tsx
// frontend/src/features/types/detail/type-custom-fields-display.tsx
import type { TypeRead } from "@/features/assets/types";

type Field = TypeRead["custom_fields"][number];

/** 类型只读视图里的 custom_fields schema 展示（只读，非编辑）。 */
export function TypeCustomFieldsDisplay({ fields }: { fields: Field[] }) {
  if (fields.length === 0) {
    return <p className="text-sm text-muted-foreground">无自定义字段</p>;
  }
  return (
    <ul className="divide-y divide-border/50">
      {fields.map((f) => (
        <li
          key={f.key}
          className="grid grid-cols-[1fr_auto] items-baseline gap-4 py-3 text-sm"
        >
          <div className="space-y-0.5">
            <div className="flex items-center gap-2">
              <span className="font-medium">{f.label || f.key}</span>
              <span className="font-code text-xs text-muted-foreground">{f.key}</span>
              {f.required && (
                <span className="text-xs text-muted-foreground">· 必填</span>
              )}
            </div>
            {f.options && f.options.length > 0 && (
              <p className="text-xs text-muted-foreground">
                选项：{f.options.join("、")}
              </p>
            )}
          </div>
          <span className="font-code text-xs text-muted-foreground">{f.type}</span>
        </li>
      ))}
    </ul>
  );
}
```

- [ ] **Step 4: 跑测试确认通过**

Run: `pnpm --dir frontend exec vitest run tests/unit/type-custom-fields-display.test.tsx`
Expected: PASS（2 通过）

- [ ] **Step 5: 提交**

```bash
git add frontend/src/features/types/detail/type-custom-fields-display.tsx frontend/tests/unit/type-custom-fields-display.test.tsx
git commit -m "feat(frontend): 类型只读 custom_fields schema 展示组件"
```

---

## Task 4: 类型只读视图 TypeDetailView

**Files:**
- Create: `frontend/src/features/types/detail/type-detail-view.tsx`
- Test: `frontend/tests/components/type-detail-view.test.tsx`

镜像资产详情只读区：DetailPageShell + 元信息 dl 行（复用 `DefinitionRow`）+ custom_fields schema section + actions（编辑 + ⋯删除）。`TypeDetailView` 接收已取到的 `type: TypeRead`（数据获取留在路由组件/Task 6，便于纯组件测试）。

- [ ] **Step 1: 写失败测试**

```tsx
// frontend/tests/components/type-detail-view.test.tsx
import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import {
  createMemoryHistory,
  createRouter,
  RouterProvider,
  createRootRoute,
  createRoute,
  Outlet,
} from "@tanstack/react-router";

import { TypeDetailView } from "@/features/types/detail/type-detail-view";
import type { TypeRead } from "@/features/assets/types";

const type: TypeRead = {
  id: "t1",
  name: "笔记本",
  code_prefix: "NB",
  description: "便携电脑",
  custom_fields: [],
  ref_count: 3,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-02-01T00:00:00Z",
} as TypeRead;

function renderWithRouter(ui: React.ReactNode) {
  const rootRoute = createRootRoute({ component: () => <Outlet /> });
  const indexRoute = createRoute({
    getParentRoute: () => rootRoute,
    path: "/",
    component: () => <>{ui}</>,
  });
  const router = createRouter({
    routeTree: rootRoute.addChildren([indexRoute]),
    history: createMemoryHistory({ initialEntries: ["/"] }),
  });
  return render(<RouterProvider router={router} />);
}

describe("TypeDetailView", () => {
  it("渲染类型名标题 + 返回链接 + 元信息 + 资产引用数", () => {
    renderWithRouter(<TypeDetailView type={type} onDelete={vi.fn()} />);
    expect(screen.getByRole("heading", { name: "笔记本" })).toBeInTheDocument();
    expect(screen.getByText("← 返回类型列表")).toBeInTheDocument();
    expect(screen.getByText("NB")).toBeInTheDocument();
    expect(screen.getByText("3")).toBeInTheDocument(); // ref_count
  });

  it("有编辑按钮", () => {
    renderWithRouter(<TypeDetailView type={type} onDelete={vi.fn()} />);
    expect(screen.getByRole("link", { name: "编辑" })).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: 跑测试确认失败**

Run: `pnpm --dir frontend exec vitest run tests/components/type-detail-view.test.tsx`
Expected: FAIL（模块不存在）

- [ ] **Step 3: 写实现**

```tsx
// frontend/src/features/types/detail/type-detail-view.tsx
import { Link } from "@tanstack/react-router";
import { MoreHorizontal } from "lucide-react";

import { DetailPageShell } from "@/components/layout/detail-page-shell";
import { DefinitionRow } from "@/features/assets/detail/definition-row";
import { SectionTitle } from "@/components/ui/section-heading";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { formatDateTime } from "@/lib/date";
import type { TypeRead } from "@/features/assets/types";

import { TypeCustomFieldsDisplay } from "./type-custom-fields-display";

interface Props {
  type: TypeRead;
  onDelete: () => void;
}

export function TypeDetailView({ type, onDelete }: Props) {
  return (
    <DetailPageShell
      backLink={
        <Link
          to="/types"
          className="text-sm text-muted-foreground hover:text-foreground transition-colors"
        >
          ← 返回类型列表
        </Link>
      }
      title={type.name}
      meta={
        <p className="font-code text-sm text-muted-foreground">{type.code_prefix}</p>
      }
      actions={
        <div className="flex items-center gap-2">
          <Button variant="outline" asChild>
            <Link to="/types/$id/edit" params={{ id: type.id }}>
              编辑
            </Link>
          </Button>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon" aria-label="更多操作">
                <MoreHorizontal className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem
                onSelect={onDelete}
                className="text-destructive focus:text-destructive"
              >
                删除…
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      }
    >
      <section>
        <SectionTitle>元信息</SectionTitle>
        <dl className="divide-y divide-border/50">
          <DefinitionRow label="名称">{type.name}</DefinitionRow>
          <DefinitionRow label="代号前缀">
            <span className="font-code">{type.code_prefix}</span>
          </DefinitionRow>
          <DefinitionRow label="描述">
            {type.description || <span className="text-muted-foreground">—</span>}
          </DefinitionRow>
          <DefinitionRow label="资产引用数">{type.ref_count}</DefinitionRow>
          <DefinitionRow label="创建时间">
            <time className="font-code">{formatDateTime(type.created_at)}</time>
          </DefinitionRow>
          <DefinitionRow label="最后更新">
            <time className="font-code">{formatDateTime(type.updated_at)}</time>
          </DefinitionRow>
        </dl>
      </section>

      <section>
        <SectionTitle>自定义字段</SectionTitle>
        <TypeCustomFieldsDisplay fields={type.custom_fields} />
      </section>
    </DetailPageShell>
  );
}
```

- [ ] **Step 4: 跑测试确认通过**

Run: `pnpm --dir frontend exec vitest run tests/components/type-detail-view.test.tsx`
Expected: PASS（2 通过）

- [ ] **Step 5: 提交**

```bash
git add frontend/src/features/types/detail/type-detail-view.tsx frontend/tests/components/type-detail-view.test.tsx
git commit -m "feat(frontend): 类型只读视图 TypeDetailView（DetailPageShell + 元信息 + 字段 schema）"
```

---

## Task 5: 类型编辑页 + 路由 `/types/$id/edit`

**Files:**
- Create: `frontend/src/features/types/detail/type-edit-page.tsx`
- Create: `frontend/src/routes/types.$id.edit.tsx`

把原 `type-detail-page.tsx` 的「取数据 + TypeForm」职责搬到独立编辑页，对应 `assets.$id.edit`。

- [ ] **Step 1: 写编辑页组件**

```tsx
// frontend/src/features/types/detail/type-edit-page.tsx
import { useNavigate } from "@tanstack/react-router";
import { Link } from "@tanstack/react-router";

import { useTypeQuery } from "@/api/hooks/types";
import { ErrorState } from "@/components/feedback/error-state";
import { Skeleton } from "@/components/ui/skeleton";
import { isHttpError } from "@/lib/error";
import { TypeForm } from "../form/type-form";
import { TypeNotFound } from "./type-not-found";

export function TypeEditPage({ id }: { id: string }) {
  const navigate = useNavigate();
  const q = useTypeQuery(id);

  if (q.isLoading) return <Skeleton className="h-96 w-full" />;
  if (q.isError) {
    const is404 = isHttpError(q.error) && q.error.status === 404;
    if (is404) return <TypeNotFound />;
    return <ErrorState error={q.error} onRetry={() => q.refetch()} />;
  }
  if (!q.data) return null;

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <Link
        to="/types/$id"
        params={{ id }}
        className="text-sm text-muted-foreground hover:text-foreground transition-colors"
      >
        ← 返回类型详情
      </Link>
      <h1 className="text-2xl font-semibold">编辑类型 · {q.data.name}</h1>
      <TypeForm
        mode="edit"
        initial={q.data}
        // 成功后回详情页；useUpdateTypeMutation.onSuccess 已 invalidate detail
        onSuccess={() => navigate({ to: "/types/$id", params: { id } })}
      />
    </div>
  );
}
```

- [ ] **Step 2: 写路由**

```tsx
// frontend/src/routes/types.$id.edit.tsx
import { createFileRoute } from "@tanstack/react-router";
import { TypeEditPage } from "@/features/types/detail/type-edit-page";

function TypeEditRoute() {
  const { id } = Route.useParams();
  return <TypeEditPage id={id} />;
}

export const Route = createFileRoute("/types/$id/edit")({
  component: TypeEditRoute,
});
```

- [ ] **Step 3: 跑类型校验确认路由树自洽**

Run: `pnpm --dir frontend exec tsc -b`
Expected: 无错误（TanStack Router 插件会重新生成 `routeTree.gen.ts`；若用 dev server 生成，先跑一次 `pnpm --dir frontend dev` 让插件生成路由树后再 `tsc -b`。CI 走 build 流程会自动生成）

注：`TypeForm` 的 `onSuccess` 之前是 `() => {}`（原地 refetch）；改为跳详情页符合"详情/编辑分离"。`TypeForm` 内"取消"按钮 `navigate({ to: '/types' })` 保持（回列表）——可接受，或后续改回详情，本 PR 不强求。

- [ ] **Step 4: 提交**

```bash
git add frontend/src/features/types/detail/type-edit-page.tsx frontend/src/routes/types.$id.edit.tsx
git commit -m "feat(frontend): 类型编辑独立页 + /types/\$id/edit 路由"
```

---

## Task 6: 拆 `/types/$id` 为 Outlet 布局 + index 详情路由 + 清理旧合并页

**Files:**
- Modify: `frontend/src/routes/types.$id.tsx` — 转为 Outlet 布局层
- Create: `frontend/src/routes/types.$id.index.tsx` — 只读详情路由
- Delete: `frontend/src/features/types/detail/type-detail-page.tsx`
- Delete: `frontend/src/features/types/detail/type-summary-card.tsx`

**关键**：file-based 路由里要支持 `/types/$id`（详情）+ `/types/$id/edit`（编辑）两个子路由，`types.$id.tsx` 必须像 `assets.$id.tsx` 一样**转成 Outlet 布局层**，详情内容下沉到 `types.$id.index.tsx`。旧的 `max-w-3xl` 靠左容器一并去掉（shell 自带居中 960）。

- [ ] **Step 1: `types.$id.tsx` 转 Outlet 布局（镜像 `assets.$id.tsx`）**

整体替换为：

```tsx
import { createFileRoute, Outlet } from "@tanstack/react-router";
import { z } from "zod";
import { TypeNotFound } from "@/features/types/detail/type-not-found";

export const Route = createFileRoute("/types/$id")({
  parseParams: ({ id }) => ({ id: z.string().uuid().parse(id) }),
  component: () => <Outlet />,
  errorComponent: TypeNotFound,
});
```

- [ ] **Step 2: 新建 `types.$id.index.tsx` 只读详情路由**

```tsx
import { useState } from "react";
import { createFileRoute, useNavigate } from "@tanstack/react-router";

import { useTypeQuery } from "@/api/hooks/types";
import { ErrorState } from "@/components/feedback/error-state";
import { Skeleton } from "@/components/ui/skeleton";
import { isHttpError } from "@/lib/error";
import { TypeDetailView } from "@/features/types/detail/type-detail-view";
import { TypeDeleteDialog } from "@/features/types/detail/type-delete-dialog";
import { TypeNotFound } from "@/features/types/detail/type-not-found";

function TypeDetailRoute() {
  const { id } = Route.useParams();
  const navigate = useNavigate();
  const q = useTypeQuery(id);
  const [deleting, setDeleting] = useState(false);

  if (q.isLoading) return <Skeleton className="h-96 w-full" />;
  if (q.isError) {
    const is404 = isHttpError(q.error) && q.error.status === 404;
    if (is404) return <TypeNotFound />;
    return <ErrorState error={q.error} onRetry={() => q.refetch()} />;
  }
  if (!q.data) return null;

  return (
    <>
      <TypeDetailView type={q.data} onDelete={() => setDeleting(true)} />
      {deleting && (
        <TypeDeleteDialog
          type={q.data}
          onClose={() => setDeleting(false)}
          onDeleted={() => navigate({ to: "/types" })}
        />
      )}
    </>
  );
}

export const Route = createFileRoute("/types/$id/")({
  component: TypeDetailRoute,
});
```

- [ ] **Step 3: 删除旧文件**

```bash
git rm frontend/src/features/types/detail/type-detail-page.tsx frontend/src/features/types/detail/type-summary-card.tsx
```

- [ ] **Step 4: 确认无残留引用 + 路由树自洽**

先让路由插件重新生成路由树（dev server 或 build）：`pnpm --dir frontend dev`（起来后即可 Ctrl-C；插件会写 `routeTree.gen.ts`，新增 `/types/$id/` 与 `/types/$id/edit`）。
Run: `pnpm --dir frontend exec tsc -b`
Expected: 无错误。若报 `type-summary-card` / `type-detail-page` 被引用，grep 找出并清理（预期已无引用——原 `types.$id.tsx` 的旧 import 已在 Step 1 移除）。

补充检查：grep `type-detail-page` 与 `type-summary-card` 在 `frontend/src` + `frontend/tests`。若 `frontend/tests` 有针对旧组件的测试，删除或迁移到 `type-detail-view.test.tsx`。

- [ ] **Step 5: 提交**

```bash
git add frontend/src/routes/types.$id.tsx frontend/src/routes/types.$id.index.tsx frontend/src/routes/routeTree.gen.ts
git commit -m "refactor(frontend): 拆 /types/\$id 为 Outlet 布局 + index 只读详情，删除旧合并页与 TypeSummaryCard"
```

---

## Task 7: 全量验证 + e2e 烟测 + 收尾

**Files:**
- 可能 Modify: `frontend/e2e/specs/`（如已有 types 流程 spec 需适配新路由）

- [ ] **Step 1: 全量前端测试**

Run: `pnpm --dir frontend test`
Expected: 全绿（含新增 detail-page-shell / type-custom-fields-display / type-detail-view 测试，及适配后的 asset-header 测试）

- [ ] **Step 2: 类型校验（tsc -b，非 --noEmit）**

Run: `pnpm --dir frontend exec tsc -b`
Expected: 无错误（CLAUDE.md / memory：必须 `tsc -b`，单 pass `--noEmit` 会漏真错）

- [ ] **Step 3: lint + 反 AI-slop 红线**

Run: `pnpm --dir frontend lint`
Expected: 无错误
Run（红线，期望 0 命中；本 PR 无渐变/动画新增）: `grep -rnE "scale-|animate-spin|backdrop-blur|bg-gradient-to" frontend/src/components/layout/detail-page-shell.tsx frontend/src/features/types/detail/`
Expected: 0 命中

- [ ] **Step 4: Playwright MCP 烟测（关键流程）**

启动 `uv run asset-hub serve start --mode dev`，用 playwright MCP 走：
1. `/types` → 点一行 → `/types/$id` 只读视图（返回链接 + 编辑按钮 + 元信息 + 字段 schema 都在，**居中** 960）
2. 只读视图点「编辑」→ `/types/$id/edit` 表单页（返回详情链接 + TypeForm）
3. 编辑保存 → 跳回 `/types/$id` 详情，改动生效
4. `/assets/$id` 详情视觉与改造前一致（返回/标题/角标/操作区/各 section 不变）
5. 截图对比 `/types/$id` 与 `/assets/$id` 现在「一家人」

- [ ] **Step 5: 推 PR**

```bash
git push -u origin HEAD
gh pr create --title "feat(frontend): 类型详情对齐资产架构 + DetailPageShell 抽取（§W-详情）" --body "$(cat <<'BODY'
实现 spec docs/superpowers/specs/2026-05-26-ui-consistency-batch-design.md 的 §W-详情：

- 抽 DetailPageShell 详情页共享骨架（居中 960 + 返回 + 标题/meta/actions slot）
- 资产详情改用 shell（视觉不变；导出 AssetActionArea/AssetMeta/AssetTitleAccessory）
- 类型详情拆「只读视图 TypeDetailView + 独立编辑页 /types/\$id/edit」完全对齐资产
- 补类型详情返回按钮、居中、删除收进 ⋯ 菜单；删除旧合并页与 TypeSummaryCard

纯前端，无 schema/后端改动。

🤖 Generated with [Claude Code](https://claude.com/claude-code)
BODY
)"
```

---

## Self-Review

**Spec 覆盖（§W-详情 / 决策 1-3）：** DetailPageShell（决策 3）= Task 1；资产改用（决策 3）= Task 2；只读类型视图（决策 2，含 ref_count + custom_fields schema + 编辑/⋯删除）= Task 3+4+6；拆编辑页（§W-详情）= Task 5；容器居中 + 返回按钮 + 删除收菜单 = Task 4/6。决策 1（page-header）属 PR-2，不在本计划。✅ 覆盖完整。

**占位符扫描：** 无 TBD/TODO；新组件与测试均给完整代码；修改给完整替换块或精确行号。✅

**类型一致性：** `DetailPageShell` props（`backLink/title/titleAccessory/meta/actions/children`）在 Task 1 定义，Task 2/4 一致使用；`AssetActionArea/AssetMeta/AssetTitleAccessory` Task 2 定义并在 asset-detail-page 使用；`TypeCustomFieldsDisplay`（Task 3）被 `TypeDetailView`（Task 4）用 `fields` prop 调用一致；`TypeDetailView` props（`type/onDelete`）在 Task 4 定义、Task 6 路由一致传入。✅

**注意点：** `ref_count` / `custom_fields` 已在 `TypeRead`（M2c-4），无需后端改动；TanStack Router file-based 新增 `types.$id.edit.tsx` 后路由树由插件再生成（dev/build 时），`tsc -b` 前确保路由树已生成。
