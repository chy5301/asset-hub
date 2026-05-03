# M3a PR-2 实施计划：前端切换 + UX 完整

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** M3a PR-2 落地——前端切到新 transitions 端点 + 7 dialog 组件改造（按 status token 染色 + AlertDialog/Dialog 按可逆性区分）+ 列表 Toggle chip 替代 checkbox + 新增 `--status-disposed` OKLCH token + 5 态文案修订 + timeline 10 kind icon × token 配置 + simplify §J/§L 顺手清理 + playwright MCP 烟测。

**Architecture:** 前端切到 `useTransitionsQuery` / `useRecordTransitionMutation`；详情页 7 个 dialog（DisposeAlertDialog / RetireAlertDialog / CheckoutDialog / ReturnDialog / RelocateDialog / TransferHolderDialog / SimpleTransitionDialog 共用 3 简单 kind）；⋯ 菜单按 status 静态过滤；列表 Toggle chip with status token；timeline 10 kind 配置驱动渲染（沿用 M2c-2 卡片堆叠形态，不做 §14.8 视觉重构）。

**Tech Stack:** React 19、TanStack Router/Query、shadcn/ui、Tailwind v4、TypeScript 6、openapi-fetch、RHF + Zod、vitest、Playwright MCP。

**Spec:** [`docs/superpowers/specs/2026-05-03-m3a-state-machine-design.md`](../specs/2026-05-03-m3a-state-machine-design.md)

**前置约束**：

- **PR-1 必须已合并到 main**（[`2026-05-03-m3a-pr1-backend.md`](./2026-05-03-m3a-pr1-backend.md) 全部 11 任务完成）
- main 上前端 ts 类型错（旧 `CheckoutRead` 等 import 失效），PR-2 第一波改动会先消除 import error
- design-system 约束：MASTER.md 反 AI-slop 红线（详见 spec §5.9）

**任务总览**（16 任务）：

1. design-system token 扩展（`--status-disposed` OKLCH pair）
2. status-labels.ts 5 态修订（含 RETIRED Icon Moon）
3. transitions hooks + query keys + 删旧 checkout hooks
4. 全前端 status/checkout type 引用清理（消除 ts 编译错）
5. ⋯ 菜单可见性配置（available-transitions.ts）
6. CheckoutDialog 升级（kind 选择器 + transitions 端点）
7. ReturnDialog 升级（"归还给"语义 + transitions 端点）
8. SimpleTransitionDialog 升级（送修 / 维修完成 / 重新启用）
9. RetireAlertDialog 新建
10. DisposeAlertDialog 新建（输入"处置"二次确认）
11. RelocateDialog 新建
12. TransferHolderDialog 新建
13. asset-header.tsx ⋯ 菜单接入新 dialog
14. 列表 Toggle chip + filter（含 search-schema 扩 + URL 持久化）
15. transition-timeline.tsx 重写（10 kind icon × token 配置）
16. simplify §J/§L 顺手清理 + PR-2 验收

---

## 任务详情

### Task 1: design-system token 扩展（`--status-disposed` OKLCH pair）

**Files:**
- Modify: `frontend/src/styles/globals.css`

- [ ] **Step 1.1: 加 light + dark variant + @theme 映射**

定位 `frontend/src/styles/globals.css` 现有 status token 段（`--status-in-use` 等附近），追加 light variant：

```css
/* light root */
--status-disposed: oklch(0.95 0.000 0);
--status-disposed-fg: oklch(0.35 0.000 0);
```

dark mode 段（`.dark` 或 `[data-theme="dark"]`）追加：

```css
--status-disposed: oklch(0.18 0.000 0);
--status-disposed-fg: oklch(0.50 0.000 0);
```

`@theme inline` 段追加：

```css
--color-status-disposed: var(--status-disposed);
--color-status-disposed-fg: var(--status-disposed-fg);
```

- [ ] **Step 1.2: 验证 tailwind utility 生成**

启动 dev server：`pnpm --dir frontend dev &`

在浏览器 devtools 控制台执行 `document.documentElement.style.setProperty('--status-disposed', 'red'); ` 验证变量存在并可被改动；恢复后关闭 dev server。

或更简单：

Run: `grep -n "status-disposed" frontend/src/styles/globals.css`
Expected: ≥ 4 行（light bg/fg + dark bg/fg），`@theme` 段亦命中

- [ ] **Step 1.3: Commit**

```bash
git add frontend/src/styles/globals.css
git commit -m "feat(design-system): 加 --status-disposed / --status-disposed-fg OKLCH token pair（light + dark + @theme 映射）"
```

---

### Task 2: status-labels.ts 5 态修订

**Files:**
- Modify: `frontend/src/features/assets/status-labels.ts`

- [ ] **Step 2.1: 全文替换**

替换 `frontend/src/features/assets/status-labels.ts`：

```typescript
import { Archive, Circle, CircleDot, Moon, Wrench, type LucideIcon } from "lucide-react";

export type AssetStatus = "IN_USE" | "IDLE" | "MAINTENANCE" | "RETIRED" | "DISPOSED";

export interface StatusMeta {
  label: string;
  bgVar: string;
  fgVar: string;
  Icon: LucideIcon;
}

export const STATUS_META: Record<AssetStatus, StatusMeta> = {
  IN_USE: {
    label: "在用",
    bgVar: "--status-in-use",
    fgVar: "--status-in-use-fg",
    Icon: CircleDot,
  },
  IDLE: {
    label: "闲置",
    bgVar: "--status-idle",
    fgVar: "--status-idle-fg",
    Icon: Circle,
  },
  MAINTENANCE: {
    label: "维修中",
    bgVar: "--status-maintenance",
    fgVar: "--status-maintenance-fg",
    Icon: Wrench,
  },
  RETIRED: {
    label: "已退役",
    bgVar: "--status-retired",
    fgVar: "--status-retired-fg",
    Icon: Moon,
  },
  DISPOSED: {
    label: "已处置",
    bgVar: "--status-disposed",
    fgVar: "--status-disposed-fg",
    Icon: Archive,
  },
};
```

修订点：
- MAINTENANCE label "维护" → "维修中"
- RETIRED label "退役" → "已退役"，Icon `MinusCircle` → `Moon`
- 新增 DISPOSED：label "已处置"，Icon `Archive`
- AssetStatus type 扩 5 态字面量

- [ ] **Step 2.2: 验证 import 路径不漂移**

Run: `grep -rn "MinusCircle\|status-labels" frontend/src --include='*.tsx' --include='*.ts'`
Expected: `MinusCircle` 0 命中（已被 Moon 替代）；`status-labels` import 路径仍正确

- [ ] **Step 2.3: Commit**

```bash
git add frontend/src/features/assets/status-labels.ts
git commit -m "feat(status-labels): 5 态文案修订（在用/闲置/维修中/已退役/已处置）+ RETIRED Icon Moon + 新增 DISPOSED"
```

---

### Task 3: transitions hooks + query keys + 删旧 checkout hooks

**Files:**
- Create: `frontend/src/api/hooks/transitions.ts`
- Modify: `frontend/src/api/query-keys.ts`
- Delete: `frontend/src/features/assets/detail/checkout-actions.ts`（如内容已无意义）
- Delete: 旧 useCheckoutHistoryQuery / useCheckout / useReturn 等 hook 文件

- [ ] **Step 3.1: 扩 query keys**

修改 `frontend/src/api/query-keys.ts`，在 `assets` namespace 下追加（沿用现有 namespace pattern）：

```typescript
export const qk = {
  // ... 现有 ...
  assets: {
    all: ["assets"] as const,
    list: (params: AssetListParams) => ["assets", "list", params] as const,
    detail: (id: string) => ["assets", "detail", id] as const,
    transitions: (id: string) => ["assets", "transitions", id] as const,  // 新增
  },
  // ... 现有 ...
} as const;
```

如果原 `qk.assets.history(id)` 存在，删除（被 `transitions(id)` 替代）。

- [ ] **Step 3.2: 写 transitions hooks**

新建 `frontend/src/api/hooks/transitions.ts`：

```typescript
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { client } from "@/api/client";
import type { components } from "@/api/generated/schema";
import { qk } from "@/api/query-keys";
import { unwrap, unwrapVoid } from "@/api/error";

type TransitionRead = components["schemas"]["TransitionRead"];
type TransitionCreate = components["schemas"]["TransitionCreate"];

export function useTransitionsQuery(assetId: string | undefined) {
  return useQuery({
    queryKey: assetId ? qk.assets.transitions(assetId) : ["disabled"],
    enabled: !!assetId,
    queryFn: async () => {
      const res = await client.GET("/api/assets/{asset_id}/transitions", {
        params: { path: { asset_id: assetId! } },
      });
      return unwrap(res);
    },
  });
}

export function useRecordTransitionMutation(assetId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: TransitionCreate): Promise<TransitionRead> => {
      const res = await client.POST("/api/assets/{asset_id}/transitions", {
        params: { path: { asset_id: assetId } },
        body,
      });
      return unwrap(res);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: qk.assets.detail(assetId) });
      qc.invalidateQueries({ queryKey: qk.assets.transitions(assetId) });
      qc.invalidateQueries({ queryKey: qk.assets.all });
    },
  });
}
```

- [ ] **Step 3.3: 删旧 checkout 相关 hook**

定位旧文件并删除（grep 之后逐个判断）：

Run: `grep -rln "useCheckoutHistoryQuery\|useCheckoutMutation\|useReturnMutation" frontend/src`

对找到的每个文件：
- 如整个文件只是 checkout/return mutation 定义 → `git rm`
- 如混用其他内容 → 删 checkout 相关 export，保留其他

特别检查：
- `frontend/src/api/hooks/` 下旧 checkout hook 文件
- `frontend/src/features/assets/detail/checkout-actions.ts`（保留 const 文案如 `CHECKOUT_VERB` 等仍被 ⋯ 菜单引用）

- [ ] **Step 3.4: 验证 ts 编译错初步消除**

Run: `pnpm --dir frontend tsc -b`
Expected: 残留 ts 错误数量减少（但因还有 dialog 引用旧 hook，预计仍有错误，下任务继续修）

- [ ] **Step 3.5: Commit**

```bash
git add frontend/src/api/hooks/transitions.ts frontend/src/api/query-keys.ts
git rm frontend/src/api/hooks/<old-checkout-hooks>.ts  # 实际文件名按 step 3.3 确认
git commit -m "feat(hooks): useTransitionsQuery + useRecordTransitionMutation；删旧 checkout/return hooks"
```

---

### Task 4: 全前端 status/checkout type 引用清理（消除 ts 编译错）

**Files:**
- Modify: 任何 import 旧 `AssetStatus` 字面量 union（4 态版）或 `CheckoutRead` 的文件

- [ ] **Step 4.1: 用 grep 找所有引用点**

Run: `grep -rn "CheckoutRead\|@/api/generated.*Checkout\|from.*checkout-dialog\|from.*return-dialog" frontend/src --include='*.tsx' --include='*.ts'`

逐个文件检查，主要在：
- `frontend/src/features/assets/detail/asset-detail-page.tsx`
- `frontend/src/features/assets/detail/asset-header.tsx`
- `frontend/src/features/assets/detail/checkout-timeline.tsx`
- `frontend/src/features/assets/detail/state-change-actions.ts`
- `frontend/src/features/assets/detail/state-change-alert.tsx`

这些文件在后续 task（5-15）逐个改造。本 task 仅修复**仅类型 import 不一致**导致的编译错（如 4 态 union 引用）：

- [ ] **Step 4.2: 升级所有 AssetStatus union 引用为 5 态**

Run: `grep -rn '"IN_USE" | "IDLE" | "MAINTENANCE" | "RETIRED"' frontend/src --include='*.tsx' --include='*.ts'`

替换为 `"IN_USE" | "IDLE" | "MAINTENANCE" | "RETIRED" | "DISPOSED"` 或改为 `import type { AssetStatus } from "@/features/assets/status-labels"`。

- [ ] **Step 4.3: 跑 tsc**

Run: `pnpm --dir frontend tsc -b`
Expected: 仍有 ts 错误（dialog/timeline 在 task 6-15 改造），但与本 task 相关的 AssetStatus union mismatch 错误应消除

- [ ] **Step 4.4: Commit**

```bash
git add frontend/src
git commit -m "chore(types): 全前端 AssetStatus 引用切到 5 态 union（消除 PR-1 后的 ts mismatch 错）"
```

---

### Task 5: ⋯ 菜单可见性配置（available-transitions.ts）

**Files:**
- Create: `frontend/src/features/assets/detail/available-transitions.ts`

- [ ] **Step 5.1: 写静态可见性配置**

新建 `frontend/src/features/assets/detail/available-transitions.ts`：

```typescript
import type { AssetStatus } from "@/features/assets/status-labels";
import type { components } from "@/api/generated/schema";

type TransitionKind = components["schemas"]["TransitionKind"];

export interface PrimaryAction {
  kind: TransitionKind | "DISPATCH_GROUP";  // DISPATCH_GROUP 表示 CHECKOUT_INTERNAL/EXTERNAL 选择
  label: string;
}

export interface MenuAction {
  kind: TransitionKind;
  label: string;
}

/** 详情页主按钮（按 status 决定唯一主操作）。DISPOSED 无主按钮。 */
export const PRIMARY_ACTION: Record<AssetStatus, PrimaryAction | null> = {
  IDLE:        { kind: "DISPATCH_GROUP",        label: "派发" },
  IN_USE:      { kind: "RETURN",                label: "归还" },
  MAINTENANCE: { kind: "RECOVER_FROM_MAINTENANCE", label: "维修完成" },
  RETIRED:     { kind: "REINSTATE",             label: "重新启用" },
  DISPOSED:    null,
};

/** ⋯ 菜单可见项（按 status 过滤）。DISPOSED 全只读，菜单为空。 */
export const MENU_ACTIONS: Record<AssetStatus, MenuAction[]> = {
  IDLE: [
    { kind: "SEND_TO_MAINTENANCE", label: "送修" },
    { kind: "RETIRE",              label: "退役" },
    { kind: "RELOCATE",            label: "变更位置" },
    { kind: "TRANSFER_HOLDER",     label: "变更保管人" },
  ],
  IN_USE: [
    { kind: "RELOCATE",            label: "变更位置" },
    { kind: "TRANSFER_HOLDER",     label: "变更保管人" },
  ],
  MAINTENANCE: [
    { kind: "RETIRE",              label: "退役" },
    { kind: "DISPOSE",             label: "处置" },
    { kind: "RELOCATE",            label: "变更位置" },
    { kind: "TRANSFER_HOLDER",     label: "变更保管人" },
  ],
  RETIRED: [
    { kind: "DISPOSE",             label: "处置" },
    { kind: "RELOCATE",            label: "变更位置" },
    { kind: "TRANSFER_HOLDER",     label: "变更保管人" },
  ],
  DISPOSED: [],
};
```

- [ ] **Step 5.2: Commit**

```bash
git add frontend/src/features/assets/detail/available-transitions.ts
git commit -m "feat(detail): available-transitions.ts 静态配置（按 status 决定主按钮 + ⋯ 菜单可见项）"
```

---

### Task 6: CheckoutDialog 升级（kind 选择器 + transitions 端点）

**Files:**
- Modify: `frontend/src/features/assets/detail/checkout-dialog.tsx`

- [ ] **Step 6.1: 重写 CheckoutDialog**

替换 `frontend/src/features/assets/detail/checkout-dialog.tsx` 整文件：

```typescript
import { ArrowRightFromLine } from "lucide-react";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";

import { useRecordTransitionMutation } from "@/api/hooks/transitions";
import { Button } from "@/components/ui/button";
import {
  Dialog, DialogContent, DialogDescription, DialogFooter,
  DialogHeader, DialogTitle, DialogTrigger,
} from "@/components/ui/dialog";
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import { toast } from "@/components/ui/use-toast";
import { toFriendlyMessage } from "@/lib/error";

const schema = z.object({
  kind: z.enum(["CHECKOUT_INTERNAL", "CHECKOUT_EXTERNAL"]).default("CHECKOUT_INTERNAL"),
  to_holder: z.string().min(1, "请输入派发对象"),
  to_location: z.string().optional(),
  due_at: z.string().optional(),
  note: z.string().optional(),
});
type FormValues = z.infer<typeof schema>;

interface Props {
  assetId: string;
  trigger: React.ReactNode;
}

export function CheckoutDialog({ assetId, trigger }: Props) {
  const [open, setOpen] = useState(false);
  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { kind: "CHECKOUT_INTERNAL", to_holder: "", to_location: "", note: "" },
  });
  const mutation = useRecordTransitionMutation(assetId);

  const onSubmit = async (values: FormValues) => {
    try {
      await mutation.mutateAsync({
        kind: values.kind,
        to_holder: values.to_holder,
        to_location: values.to_location || null,
        due_at: values.due_at || null,
        note: values.note || null,
      });
      toast({ title: values.kind === "CHECKOUT_INTERNAL" ? "已派发" : "已出借" });
      form.reset();
      setOpen(false);
    } catch (e) {
      toast({ title: "派发失败", description: toFriendlyMessage(e), variant: "destructive" });
    }
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>{trigger}</DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <div className="flex items-center gap-2">
            <span className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium bg-status-in-use/15 text-status-in-use-fg">
              <ArrowRightFromLine className="size-3.5" aria-hidden />
              派发
            </span>
          </div>
          <DialogTitle className="font-sans">派发资产</DialogTitle>
          <DialogDescription>选择派发类型并填写接收人。</DialogDescription>
        </DialogHeader>
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
            <FormField
              control={form.control}
              name="kind"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>派发类型</FormLabel>
                  <FormControl>
                    <ToggleGroup
                      type="single"
                      value={field.value}
                      onValueChange={(v) => v && field.onChange(v)}
                      className="justify-start"
                    >
                      <ToggleGroupItem value="CHECKOUT_INTERNAL" className="data-[state=on]:bg-status-in-use/15 data-[state=on]:text-status-in-use-fg">
                        派发 · 内部使用
                      </ToggleGroupItem>
                      <ToggleGroupItem value="CHECKOUT_EXTERNAL" className="data-[state=on]:bg-status-in-use/15 data-[state=on]:text-status-in-use-fg">
                        出借 · 借给外部
                      </ToggleGroupItem>
                    </ToggleGroup>
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField control={form.control} name="to_holder" render={({ field }) => (
              <FormItem>
                <FormLabel>派发给</FormLabel>
                <FormControl><Input placeholder="保管人/接收方" {...field} /></FormControl>
                <FormMessage />
              </FormItem>
            )} />
            <FormField control={form.control} name="to_location" render={({ field }) => (
              <FormItem>
                <FormLabel>位置（可选）</FormLabel>
                <FormControl><Input placeholder="如 1F-工位" {...field} /></FormControl>
              </FormItem>
            )} />
            <FormField control={form.control} name="due_at" render={({ field }) => (
              <FormItem>
                <FormLabel>期望归还时间（可选）</FormLabel>
                <FormControl><Input type="datetime-local" {...field} /></FormControl>
              </FormItem>
            )} />
            <FormField control={form.control} name="note" render={({ field }) => (
              <FormItem>
                <FormLabel>备注（可选）</FormLabel>
                <FormControl><Textarea placeholder="…" {...field} /></FormControl>
              </FormItem>
            )} />
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setOpen(false)}>取消</Button>
              <Button type="submit" disabled={mutation.isPending}>
                {mutation.isPending ? "派发中…" : "确认派发"}
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
}
```

- [ ] **Step 6.2: 如需添加 shadcn ToggleGroup 组件**

Run: `pnpm --dir frontend dlx shadcn@latest add toggle-group`
Expected: 生成 `frontend/src/components/ui/toggle-group.tsx`，按 M2c-3 §3 4 项审查清单走（删 "use client" / 不引入 next-themes / 用 token / focus-visible）

- [ ] **Step 6.3: Commit**

```bash
git add frontend/src/features/assets/detail/checkout-dialog.tsx frontend/src/components/ui/toggle-group.tsx
git commit -m "feat(dialog): CheckoutDialog 升级——kind 选择器（内部派发/对外出借） + transitions 端点 + status-in-use chip"
```

---

### Task 7: ReturnDialog 升级（"归还给"语义 + transitions 端点）

**Files:**
- Modify: `frontend/src/features/assets/detail/return-dialog.tsx`

- [ ] **Step 7.1: 重写 ReturnDialog**

替换 `frontend/src/features/assets/detail/return-dialog.tsx`：

```typescript
import { Undo2 } from "lucide-react";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";

import { useRecordTransitionMutation } from "@/api/hooks/transitions";
import { Button } from "@/components/ui/button";
import {
  Dialog, DialogContent, DialogDescription, DialogFooter,
  DialogHeader, DialogTitle, DialogTrigger,
} from "@/components/ui/dialog";
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { toast } from "@/components/ui/use-toast";
import { toFriendlyMessage } from "@/lib/error";

const schema = z.object({
  to_holder: z.string().optional(),
  to_location: z.string().optional(),
  note: z.string().optional(),
});
type FormValues = z.infer<typeof schema>;

interface Props {
  assetId: string;
  trigger: React.ReactNode;
}

export function ReturnDialog({ assetId, trigger }: Props) {
  const [open, setOpen] = useState(false);
  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { to_holder: "", to_location: "", note: "" },
  });
  const mutation = useRecordTransitionMutation(assetId);

  const onSubmit = async (values: FormValues) => {
    try {
      await mutation.mutateAsync({
        kind: "RETURN",
        to_holder: values.to_holder || null,
        to_location: values.to_location || null,
        note: values.note || null,
      });
      toast({ title: "已归还" });
      form.reset();
      setOpen(false);
    } catch (e) {
      toast({ title: "归还失败", description: toFriendlyMessage(e), variant: "destructive" });
    }
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>{trigger}</DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <div className="flex items-center gap-2">
            <span className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium bg-status-idle/15 text-status-idle-fg">
              <Undo2 className="size-3.5" aria-hidden />
              归还
            </span>
          </div>
          <DialogTitle className="font-sans">归还资产</DialogTitle>
          <DialogDescription>归还接收人将成为新 holder；不填则资产无 holder（无人值守）。</DialogDescription>
        </DialogHeader>
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
            <FormField control={form.control} name="to_holder" render={({ field }) => (
              <FormItem>
                <FormLabel>归还给（可选，留空表示无人值守）</FormLabel>
                <FormControl><Input placeholder="如：仓管李四" {...field} /></FormControl>
                <FormMessage />
              </FormItem>
            )} />
            <FormField control={form.control} name="to_location" render={({ field }) => (
              <FormItem>
                <FormLabel>归还位置（可选）</FormLabel>
                <FormControl><Input placeholder="如：1F-柜 3" {...field} /></FormControl>
              </FormItem>
            )} />
            <FormField control={form.control} name="note" render={({ field }) => (
              <FormItem>
                <FormLabel>备注（可选）</FormLabel>
                <FormControl><Textarea {...field} /></FormControl>
              </FormItem>
            )} />
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setOpen(false)}>取消</Button>
              <Button type="submit" disabled={mutation.isPending}>
                {mutation.isPending ? "归还中…" : "确认归还"}
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
}
```

- [ ] **Step 7.2: Commit**

```bash
git add frontend/src/features/assets/detail/return-dialog.tsx
git commit -m "feat(dialog): ReturnDialog 升级——'归还给'语义 + transitions 端点 + status-idle chip"
```

---

### Task 8: SimpleTransitionDialog 升级（送修 / 维修完成 / 重新启用）

**Files:**
- Rename + rewrite: `frontend/src/features/assets/detail/state-change-alert.tsx` → `simple-transition-dialog.tsx`
- Modify: 任何 import 旧 `state-change-alert` 的文件

- [ ] **Step 8.1: 写新组件**

新建 `frontend/src/features/assets/detail/simple-transition-dialog.tsx`：

```typescript
import { CheckCircle2, Sun, Wrench, type LucideIcon } from "lucide-react";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";

import { useRecordTransitionMutation } from "@/api/hooks/transitions";
import { Button } from "@/components/ui/button";
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent,
  AlertDialogDescription, AlertDialogFooter, AlertDialogHeader,
  AlertDialogTitle, AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { Form, FormControl, FormField, FormItem, FormLabel } from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { toast } from "@/components/ui/use-toast";
import { toFriendlyMessage } from "@/lib/error";
import type { components } from "@/api/generated/schema";

type TransitionKind = components["schemas"]["TransitionKind"];

interface KindMeta {
  label: string;
  description: string;
  Icon: LucideIcon;
  bgClass: string;
  fgClass: string;
}

const META: Partial<Record<TransitionKind, KindMeta>> = {
  SEND_TO_MAINTENANCE: {
    label: "送修",
    description: "资产送修后状态变为'维修中'，无法派发。",
    Icon: Wrench,
    bgClass: "bg-status-maintenance/15",
    fgClass: "text-status-maintenance-fg",
  },
  RECOVER_FROM_MAINTENANCE: {
    label: "维修完成",
    description: "维修完成后资产回到'闲置'状态。",
    Icon: CheckCircle2,
    bgClass: "bg-status-idle/15",
    fgClass: "text-status-idle-fg",
  },
  REINSTATE: {
    label: "重新启用",
    description: "重新启用退役资产，回到'闲置'状态。",
    Icon: Sun,
    bgClass: "bg-status-idle/15",
    fgClass: "text-status-idle-fg",
  },
};

const schema = z.object({
  to_holder: z.string().optional(),
  to_location: z.string().optional(),
  note: z.string().optional(),
});
type FormValues = z.infer<typeof schema>;

interface Props {
  assetId: string;
  kind: "SEND_TO_MAINTENANCE" | "RECOVER_FROM_MAINTENANCE" | "REINSTATE";
  trigger: React.ReactNode;
}

export function SimpleTransitionDialog({ assetId, kind, trigger }: Props) {
  const meta = META[kind]!;
  const [open, setOpen] = useState(false);
  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { to_holder: "", to_location: "", note: "" },
  });
  const mutation = useRecordTransitionMutation(assetId);
  const Icon = meta.Icon;

  const onConfirm = async () => {
    const values = form.getValues();
    try {
      await mutation.mutateAsync({
        kind,
        to_holder: values.to_holder || null,
        to_location: values.to_location || null,
        note: values.note || null,
      });
      toast({ title: `已${meta.label}` });
      form.reset();
      setOpen(false);
    } catch (e) {
      toast({ title: `${meta.label}失败`, description: toFriendlyMessage(e), variant: "destructive" });
    }
  };

  return (
    <AlertDialog open={open} onOpenChange={setOpen}>
      <AlertDialogTrigger asChild>{trigger}</AlertDialogTrigger>
      <AlertDialogContent>
        <AlertDialogHeader>
          <div className="flex items-center gap-2">
            <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium ${meta.bgClass} ${meta.fgClass}`}>
              <Icon className="size-3.5" aria-hidden />
              {meta.label}
            </span>
          </div>
          <AlertDialogTitle className="font-sans">{meta.label}资产</AlertDialogTitle>
          <AlertDialogDescription>{meta.description}</AlertDialogDescription>
        </AlertDialogHeader>
        <Form {...form}>
          <form className="space-y-4">
            <FormField control={form.control} name="to_holder" render={({ field }) => (
              <FormItem>
                <FormLabel>保管人（可选）</FormLabel>
                <FormControl><Input {...field} /></FormControl>
              </FormItem>
            )} />
            <FormField control={form.control} name="to_location" render={({ field }) => (
              <FormItem>
                <FormLabel>位置（可选）</FormLabel>
                <FormControl><Input {...field} /></FormControl>
              </FormItem>
            )} />
            <FormField control={form.control} name="note" render={({ field }) => (
              <FormItem>
                <FormLabel>备注（可选）</FormLabel>
                <FormControl><Textarea {...field} /></FormControl>
              </FormItem>
            )} />
          </form>
        </Form>
        <AlertDialogFooter>
          <AlertDialogCancel>取消</AlertDialogCancel>
          <AlertDialogAction onClick={onConfirm} disabled={mutation.isPending}>
            {mutation.isPending ? "处理中…" : `确认${meta.label}`}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
```

- [ ] **Step 8.2: 删旧 state-change-alert.tsx**

```bash
git rm frontend/src/features/assets/detail/state-change-alert.tsx
```

如有 `state-change-actions.ts` 仍含意义则保留 const；否则一并删除（在 task 13 处理 asset-header 时确认）。

- [ ] **Step 8.3: Commit**

```bash
git add frontend/src/features/assets/detail/simple-transition-dialog.tsx
git commit -m "feat(dialog): SimpleTransitionDialog 服务 SEND_TO_MAINTENANCE/RECOVER/REINSTATE 三 kind（按 status token 染色）"
```

---

### Task 9: RetireAlertDialog 新建

**Files:**
- Create: `frontend/src/features/assets/detail/retire-alert-dialog.tsx`

- [ ] **Step 9.1: 写组件**

新建 `frontend/src/features/assets/detail/retire-alert-dialog.tsx`：

```typescript
import { Moon } from "lucide-react";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";

import { useRecordTransitionMutation } from "@/api/hooks/transitions";
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent,
  AlertDialogDescription, AlertDialogFooter, AlertDialogHeader,
  AlertDialogTitle, AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { Form, FormControl, FormField, FormItem, FormLabel } from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { toast } from "@/components/ui/use-toast";
import { toFriendlyMessage } from "@/lib/error";

const schema = z.object({
  to_holder: z.string().optional(),
  to_location: z.string().optional(),
  note: z.string().optional(),
});
type FormValues = z.infer<typeof schema>;

interface Props {
  assetId: string;
  assetName: string;
  trigger: React.ReactNode;
}

export function RetireAlertDialog({ assetId, assetName, trigger }: Props) {
  const [open, setOpen] = useState(false);
  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { to_holder: "", to_location: "", note: "" },
  });
  const mutation = useRecordTransitionMutation(assetId);

  const onConfirm = async () => {
    const v = form.getValues();
    try {
      await mutation.mutateAsync({
        kind: "RETIRE",
        to_holder: v.to_holder || null,
        to_location: v.to_location || null,
        note: v.note || null,
      });
      toast({ title: "已退役" });
      form.reset();
      setOpen(false);
    } catch (e) {
      toast({ title: "退役失败", description: toFriendlyMessage(e), variant: "destructive" });
    }
  };

  return (
    <AlertDialog open={open} onOpenChange={setOpen}>
      <AlertDialogTrigger asChild>{trigger}</AlertDialogTrigger>
      <AlertDialogContent>
        <AlertDialogHeader>
          <div className="flex items-center gap-2">
            <span className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium bg-status-retired/15 text-status-retired-fg">
              <Moon className="size-3.5" aria-hidden />
              退役
            </span>
          </div>
          <AlertDialogTitle className="font-sans">退役 {assetName}？</AlertDialogTitle>
          <AlertDialogDescription>
            退役后资产可通过"重新启用"恢复至闲置状态。可选填备件库管理员、存放位置。
          </AlertDialogDescription>
        </AlertDialogHeader>
        <Form {...form}>
          <form className="space-y-4">
            <FormField control={form.control} name="to_holder" render={({ field }) => (
              <FormItem>
                <FormLabel>备件库管理员（可选）</FormLabel>
                <FormControl><Input {...field} /></FormControl>
              </FormItem>
            )} />
            <FormField control={form.control} name="to_location" render={({ field }) => (
              <FormItem>
                <FormLabel>存放位置（可选）</FormLabel>
                <FormControl><Input {...field} /></FormControl>
              </FormItem>
            )} />
            <FormField control={form.control} name="note" render={({ field }) => (
              <FormItem>
                <FormLabel>备注（可选）</FormLabel>
                <FormControl><Textarea {...field} /></FormControl>
              </FormItem>
            )} />
          </form>
        </Form>
        <AlertDialogFooter>
          <AlertDialogCancel>取消</AlertDialogCancel>
          <AlertDialogAction onClick={onConfirm} disabled={mutation.isPending}>
            {mutation.isPending ? "退役中…" : "确认退役"}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
```

- [ ] **Step 9.2: Commit**

```bash
git add frontend/src/features/assets/detail/retire-alert-dialog.tsx
git commit -m "feat(dialog): RetireAlertDialog 新建（status-retired chip + Moon icon + 可选 holder/location/note）"
```

---

### Task 10: DisposeAlertDialog 新建（输入"处置"二次确认）

**Files:**
- Create: `frontend/src/features/assets/detail/dispose-alert-dialog.tsx`

- [ ] **Step 10.1: 写组件**

新建 `frontend/src/features/assets/detail/dispose-alert-dialog.tsx`：

```typescript
import { Trash2 } from "lucide-react";
import { useState } from "react";

import { useRecordTransitionMutation } from "@/api/hooks/transitions";
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent,
  AlertDialogDescription, AlertDialogFooter, AlertDialogHeader,
  AlertDialogTitle, AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { buttonVariants } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { toast } from "@/components/ui/use-toast";
import { cn } from "@/lib/utils";
import { toFriendlyMessage } from "@/lib/error";

const CONFIRM_PHRASE = "处置";

interface Props {
  assetId: string;
  assetName: string;
  trigger: React.ReactNode;
}

export function DisposeAlertDialog({ assetId, assetName, trigger }: Props) {
  const [open, setOpen] = useState(false);
  const [confirmText, setConfirmText] = useState("");
  const [note, setNote] = useState("");
  const mutation = useRecordTransitionMutation(assetId);

  const unlocked = confirmText === CONFIRM_PHRASE;

  const onConfirm = async () => {
    try {
      await mutation.mutateAsync({
        kind: "DISPOSE",
        note: note || null,
      });
      toast({ title: "已处置" });
      setConfirmText("");
      setNote("");
      setOpen(false);
    } catch (e) {
      toast({ title: "处置失败", description: toFriendlyMessage(e), variant: "destructive" });
    }
  };

  return (
    <AlertDialog open={open} onOpenChange={(o) => { if (!o) { setConfirmText(""); setNote(""); } setOpen(o); }}>
      <AlertDialogTrigger asChild>{trigger}</AlertDialogTrigger>
      <AlertDialogContent>
        <AlertDialogHeader>
          <div className="flex items-center gap-2">
            <span className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium bg-destructive/15 text-destructive">
              <Trash2 className="size-3.5" aria-hidden />
              处置
            </span>
          </div>
          <AlertDialogTitle className="font-sans">处置 {assetName}？</AlertDialogTitle>
          <AlertDialogDescription>
            <strong>此操作不可撤销</strong>。资产 holder 与 location 将被清空，状态置为已处置。
            如需确认，请在下方输入"{CONFIRM_PHRASE}"二字。
          </AlertDialogDescription>
        </AlertDialogHeader>
        <div className="space-y-3">
          <Input
            value={confirmText}
            onChange={(e) => setConfirmText(e.target.value)}
            placeholder={`输入"${CONFIRM_PHRASE}"以解锁`}
            autoComplete="off"
          />
          <Textarea
            value={note}
            onChange={(e) => setNote(e.target.value)}
            placeholder="备注（可选，如卖给/捐赠/销毁原因）"
          />
        </div>
        <AlertDialogFooter>
          <AlertDialogCancel>取消</AlertDialogCancel>
          <AlertDialogAction
            onClick={onConfirm}
            disabled={!unlocked || mutation.isPending}
            className={cn(buttonVariants({ variant: "destructive" }))}
          >
            {mutation.isPending ? "处置中…" : "确认处置"}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
```

- [ ] **Step 10.2: Commit**

```bash
git add frontend/src/features/assets/detail/dispose-alert-dialog.tsx
git commit -m "feat(dialog): DisposeAlertDialog 新建（destructive chip + Trash2 + 输入'处置'二次确认）"
```

---

### Task 11: RelocateDialog 新建

**Files:**
- Create: `frontend/src/features/assets/detail/relocate-dialog.tsx`

- [ ] **Step 11.1: 写组件**

新建 `frontend/src/features/assets/detail/relocate-dialog.tsx`：

```typescript
import { MapPin } from "lucide-react";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";

import { useRecordTransitionMutation } from "@/api/hooks/transitions";
import { Button } from "@/components/ui/button";
import {
  Dialog, DialogContent, DialogDescription, DialogFooter,
  DialogHeader, DialogTitle, DialogTrigger,
} from "@/components/ui/dialog";
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { toast } from "@/components/ui/use-toast";
import { toFriendlyMessage } from "@/lib/error";

const schema = z.object({
  to_location: z.string().min(1, "请输入新位置"),
  note: z.string().optional(),
});
type FormValues = z.infer<typeof schema>;

interface Props {
  assetId: string;
  trigger: React.ReactNode;
}

export function RelocateDialog({ assetId, trigger }: Props) {
  const [open, setOpen] = useState(false);
  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { to_location: "", note: "" },
  });
  const mutation = useRecordTransitionMutation(assetId);

  const onSubmit = async (v: FormValues) => {
    try {
      await mutation.mutateAsync({
        kind: "RELOCATE",
        to_location: v.to_location,
        note: v.note || null,
      });
      toast({ title: "位置已变更" });
      form.reset();
      setOpen(false);
    } catch (e) {
      toast({ title: "变更位置失败", description: toFriendlyMessage(e), variant: "destructive" });
    }
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>{trigger}</DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <div className="flex items-center gap-2">
            <span className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium bg-muted text-muted-foreground">
              <MapPin className="size-3.5" aria-hidden />
              变更位置
            </span>
          </div>
          <DialogTitle className="font-sans">变更资产位置</DialogTitle>
          <DialogDescription>仅变更位置；保管人不变，状态不变。</DialogDescription>
        </DialogHeader>
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
            <FormField control={form.control} name="to_location" render={({ field }) => (
              <FormItem>
                <FormLabel>新位置</FormLabel>
                <FormControl><Input placeholder="如：1F-柜 3" {...field} /></FormControl>
                <FormMessage />
              </FormItem>
            )} />
            <FormField control={form.control} name="note" render={({ field }) => (
              <FormItem>
                <FormLabel>备注（可选）</FormLabel>
                <FormControl><Textarea {...field} /></FormControl>
              </FormItem>
            )} />
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setOpen(false)}>取消</Button>
              <Button type="submit" disabled={mutation.isPending}>
                {mutation.isPending ? "变更中…" : "确认变更"}
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
}
```

- [ ] **Step 11.2: Commit**

```bash
git add frontend/src/features/assets/detail/relocate-dialog.tsx
git commit -m "feat(dialog): RelocateDialog 新建（muted chip + MapPin + to_location 必填）"
```

---

### Task 12: TransferHolderDialog 新建

**Files:**
- Create: `frontend/src/features/assets/detail/transfer-holder-dialog.tsx`

- [ ] **Step 12.1: 写组件**

新建 `frontend/src/features/assets/detail/transfer-holder-dialog.tsx`：

```typescript
import { UserCog } from "lucide-react";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";

import { useRecordTransitionMutation } from "@/api/hooks/transitions";
import { Button } from "@/components/ui/button";
import {
  Dialog, DialogContent, DialogDescription, DialogFooter,
  DialogHeader, DialogTitle, DialogTrigger,
} from "@/components/ui/dialog";
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { toast } from "@/components/ui/use-toast";
import { toFriendlyMessage } from "@/lib/error";

const schema = z.object({
  to_holder: z.string().min(1, "请输入新保管人"),
  to_location: z.string().optional(),
  note: z.string().optional(),
});
type FormValues = z.infer<typeof schema>;

interface Props {
  assetId: string;
  trigger: React.ReactNode;
}

export function TransferHolderDialog({ assetId, trigger }: Props) {
  const [open, setOpen] = useState(false);
  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { to_holder: "", to_location: "", note: "" },
  });
  const mutation = useRecordTransitionMutation(assetId);

  const onSubmit = async (v: FormValues) => {
    try {
      await mutation.mutateAsync({
        kind: "TRANSFER_HOLDER",
        to_holder: v.to_holder,
        to_location: v.to_location || null,
        note: v.note || null,
      });
      toast({ title: "保管人已变更" });
      form.reset();
      setOpen(false);
    } catch (e) {
      toast({ title: "变更保管人失败", description: toFriendlyMessage(e), variant: "destructive" });
    }
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>{trigger}</DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <div className="flex items-center gap-2">
            <span className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium bg-muted text-muted-foreground">
              <UserCog className="size-3.5" aria-hidden />
              变更保管人
            </span>
          </div>
          <DialogTitle className="font-sans">变更保管人</DialogTitle>
          <DialogDescription>变更保管人，可同时变更位置；状态不变。</DialogDescription>
        </DialogHeader>
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
            <FormField control={form.control} name="to_holder" render={({ field }) => (
              <FormItem>
                <FormLabel>新保管人</FormLabel>
                <FormControl><Input {...field} /></FormControl>
                <FormMessage />
              </FormItem>
            )} />
            <FormField control={form.control} name="to_location" render={({ field }) => (
              <FormItem>
                <FormLabel>新位置（可选）</FormLabel>
                <FormControl><Input {...field} /></FormControl>
              </FormItem>
            )} />
            <FormField control={form.control} name="note" render={({ field }) => (
              <FormItem>
                <FormLabel>备注（可选）</FormLabel>
                <FormControl><Textarea {...field} /></FormControl>
              </FormItem>
            )} />
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setOpen(false)}>取消</Button>
              <Button type="submit" disabled={mutation.isPending}>
                {mutation.isPending ? "变更中…" : "确认变更"}
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
}
```

- [ ] **Step 12.2: Commit**

```bash
git add frontend/src/features/assets/detail/transfer-holder-dialog.tsx
git commit -m "feat(dialog): TransferHolderDialog 新建（muted chip + UserCog + to_holder 必填）"
```

---

### Task 13: asset-header.tsx ⋯ 菜单接入新 dialog

**Files:**
- Modify: `frontend/src/features/assets/detail/asset-header.tsx`

- [ ] **Step 13.1: 重写主按钮 + ⋯ 菜单逻辑**

修改 `frontend/src/features/assets/detail/asset-header.tsx`：

主体结构（伪代码示意；按文件原结构调整）：

```typescript
import { CheckoutDialog } from "./checkout-dialog";
import { ReturnDialog } from "./return-dialog";
import { SimpleTransitionDialog } from "./simple-transition-dialog";
import { RetireAlertDialog } from "./retire-alert-dialog";
import { DisposeAlertDialog } from "./dispose-alert-dialog";
import { RelocateDialog } from "./relocate-dialog";
import { TransferHolderDialog } from "./transfer-holder-dialog";
import { MENU_ACTIONS, PRIMARY_ACTION } from "./available-transitions";

// 在 component 内：
const status = asset.status;
const primary = PRIMARY_ACTION[status];
const menuItems = MENU_ACTIONS[status];

// 主按钮渲染：
function renderPrimary() {
  if (!primary) return null;  // DISPOSED 无主按钮
  if (primary.kind === "DISPATCH_GROUP") {
    return <CheckoutDialog assetId={asset.id} trigger={<Button>派发</Button>} />;
  }
  if (primary.kind === "RETURN") {
    return <ReturnDialog assetId={asset.id} trigger={<Button>归还</Button>} />;
  }
  if (primary.kind === "RECOVER_FROM_MAINTENANCE") {
    return (
      <SimpleTransitionDialog
        assetId={asset.id}
        kind="RECOVER_FROM_MAINTENANCE"
        trigger={<Button>维修完成</Button>}
      />
    );
  }
  if (primary.kind === "REINSTATE") {
    return (
      <SimpleTransitionDialog
        assetId={asset.id}
        kind="REINSTATE"
        trigger={<Button>重新启用</Button>}
      />
    );
  }
  return null;
}

// ⋯ 菜单项渲染（每项 wrap 对应 dialog 的 trigger）：
function renderMenuItem(action: { kind: string; label: string }) {
  const trigger = <DropdownMenuItem onSelect={(e) => e.preventDefault()}>{action.label}</DropdownMenuItem>;
  switch (action.kind) {
    case "SEND_TO_MAINTENANCE":
      return <SimpleTransitionDialog assetId={asset.id} kind="SEND_TO_MAINTENANCE" trigger={trigger} />;
    case "RETIRE":
      return <RetireAlertDialog assetId={asset.id} assetName={asset.name} trigger={trigger} />;
    case "DISPOSE":
      return <DisposeAlertDialog assetId={asset.id} assetName={asset.name} trigger={trigger} />;
    case "RELOCATE":
      return <RelocateDialog assetId={asset.id} trigger={trigger} />;
    case "TRANSFER_HOLDER":
      return <TransferHolderDialog assetId={asset.id} trigger={trigger} />;
    default:
      return null;
  }
}

// DISPOSED 全只读：隐藏主按钮 + ⋯ 菜单 + 编辑按钮
const isReadonly = status === "DISPOSED";
```

注意点：
- 删除任何对旧 `CheckoutDialog/ReturnDialog/StateChangeAlert` 旧 props 的引用
- 删除任何对 `state-change-actions.ts` 中已废弃 const 的引用
- 编辑按钮：DISPOSED 时隐藏（`{!isReadonly && <EditButton />}`）

- [ ] **Step 13.2: 删除（如还在）`state-change-actions.ts`**

如该文件已不被任何处引用，删除：

```bash
git rm frontend/src/features/assets/detail/state-change-actions.ts
```

否则保留尚被引用的 const，删除已无意义的部分。

- [ ] **Step 13.3: 编译验证**

Run: `pnpm --dir frontend tsc -b`
Expected: 0 错（asset-header 是大多数 dialog 的入口，前面 task 6-12 的 dialog 在此处接入后 ts 应通）

- [ ] **Step 13.4: Commit**

```bash
git add frontend/src/features/assets/detail/asset-header.tsx
git rm -f frontend/src/features/assets/detail/state-change-actions.ts  # 如已无引用
git commit -m "feat(detail): asset-header ⋯ 菜单接入 7 个 dialog（按 status 静态过滤；DISPOSED 全只读）"
```

---

### Task 14: 列表 Toggle chip + filter（含 search-schema 扩 + URL 持久化）

**Files:**
- Modify: `frontend/src/features/assets/list/search-schema.ts`
- Modify: `frontend/src/features/assets/list/assets-filters.tsx`
- Modify: `frontend/src/api/hooks/assets.ts`（如 list query 在此）
- Modify: 路由（`frontend/src/routes/index.tsx` 或 assets list route）

- [ ] **Step 14.1: 扩 search-schema**

修改 `frontend/src/features/assets/list/search-schema.ts`，加：

```typescript
export const searchSchema = z.object({
  // ... 现有字段 ...
  show_retired: z.boolean().default(false).optional(),
  show_disposed: z.boolean().default(false).optional(),
});
```

- [ ] **Step 14.2: 加 shadcn Toggle 组件（如未装）**

Run: `ls frontend/src/components/ui/toggle.tsx 2>/dev/null && echo "exists" || pnpm --dir frontend dlx shadcn@latest add toggle`

如新增，按 M2c-3 §3 4 项审查清单走（删 "use client" / 不引入 next-themes / 用 token / focus-visible）。

- [ ] **Step 14.3: 加 Toggle chip 到 assets-filters.tsx**

修改 `frontend/src/features/assets/list/assets-filters.tsx`，在 filter 区追加：

```typescript
import { Archive, Moon } from "lucide-react";
import { Toggle } from "@/components/ui/toggle";

// 在 filter 渲染区域（与现有 type/status/holder/q 同级）：
<Toggle
  size="sm"
  pressed={filters.show_retired}
  onPressedChange={(v) => onChange({ show_retired: v })}
  className="rounded-full h-7 px-3 text-xs gap-1.5 transition-colors duration-200
             data-[state=on]:bg-status-retired/15 data-[state=on]:text-status-retired-fg
             data-[state=on]:border-status-retired/30 border border-border/40"
  aria-label="显示已退役资产"
>
  <Moon className="size-3.5" aria-hidden />
  显示已退役
</Toggle>

<Toggle
  size="sm"
  pressed={filters.show_disposed}
  onPressedChange={(v) => onChange({ show_disposed: v })}
  className="rounded-full h-7 px-3 text-xs gap-1.5 transition-colors duration-200
             data-[state=on]:bg-status-disposed/15 data-[state=on]:text-status-disposed-fg
             data-[state=on]:border-status-disposed/30 border border-border/40"
  aria-label="显示已处置资产"
>
  <Archive className="size-3.5" aria-hidden />
  显示已处置
</Toggle>
```

确保 toggle 不使用 `transform: scale`、不使用 `animate-spin`/`animate-pulse`。

- [ ] **Step 14.4: 列表 query 透传 include_retired/include_disposed**

修改 `frontend/src/api/hooks/assets.ts`（或对应 hook 文件），把 `useAssetsListQuery` 接受 `include_retired`/`include_disposed` 参数并 pass 给 GET `/api/assets`：

```typescript
export function useAssetsListQuery(params: {
  type_id?: string;
  status?: string;
  holder?: string;
  q?: string;
  include_retired?: boolean;
  include_disposed?: boolean;
}) {
  return useQuery({
    queryKey: qk.assets.list(params),
    queryFn: async () => {
      const res = await client.GET("/api/assets", {
        params: { query: params },
      });
      return unwrap(res);
    },
  });
}
```

- [ ] **Step 14.5: 路由层把 search params 透传**

定位 assets list route（推测 `frontend/src/routes/index.tsx`），把 `searchSchema` 解析到的 `show_retired/show_disposed` 透传给 query：

```typescript
const search = Route.useSearch();
const query = useAssetsListQuery({
  // ... 现有 ...
  include_retired: search.show_retired ?? false,
  include_disposed: search.show_disposed ?? false,
});
```

- [ ] **Step 14.6: 编译验证**

Run: `pnpm --dir frontend tsc -b`
Expected: 0 错

- [ ] **Step 14.7: Commit**

```bash
git add frontend/src/features/assets/list/search-schema.ts frontend/src/features/assets/list/assets-filters.tsx frontend/src/api/hooks/assets.ts frontend/src/routes frontend/src/components/ui/toggle.tsx
git commit -m "feat(list): Toggle chip with status token 替代 checkbox（已退役/已处置独立 toggle + URL 持久化 + 后端 include_*）"
```

---

### Task 15: transition-timeline.tsx 重写（10 kind icon × token 配置）

**Files:**
- Rename + rewrite: `frontend/src/features/assets/detail/checkout-timeline.tsx` → `transition-timeline.tsx`
- Modify: `frontend/src/features/assets/detail/asset-detail-page.tsx`（import 路径切换）

- [ ] **Step 15.0: 先 grep 现有惯例**

Run: `grep -n "TimelineSkeleton" frontend/src/features/assets/detail/checkout-timeline.tsx`
Expected: 当前 `TimelineSkeleton` 内嵌于 `checkout-timeline.tsx` 第 ~94 行（不在 `components/feedback/skeleton`）

Run: `grep -n "bg-status-in-use\|bg-status-idle" frontend/src/features/assets/detail/checkout-timeline.tsx`
Expected: 现有 timeline 用 Tailwind utility 形式 `bg-status-in-use` / `text-status-in-use-fg`（不用 inline style + color-mix）

→ 新 `transition-timeline.tsx` 应**沿用 Tailwind utility 静态 class map**形式（与 status-badge / 现 timeline 一致）；`TimelineSkeleton` 组件继续内嵌在 transition-timeline.tsx 文件底部（不抽到 feedback/）。

- [ ] **Step 15.1: 写新 timeline 组件（Tailwind 静态 class map）**

新建 `frontend/src/features/assets/detail/transition-timeline.tsx`：

```typescript
import {
  ArrowRightFromLine, Archive, CheckCircle2, MapPin, Moon, Send,
  Sun, Trash2, Undo2, UserCog, Wrench, type LucideIcon,
} from "lucide-react";
import { format } from "date-fns";
import { zhCN } from "date-fns/locale";

import { useTransitionsQuery } from "@/api/hooks/transitions";
import { Skeleton } from "@/components/ui/skeleton";  // shadcn skeleton
import type { components } from "@/api/generated/schema";

type TransitionKind = components["schemas"]["TransitionKind"];
type TransitionRead = components["schemas"]["TransitionRead"];

interface KindMeta {
  label: string;
  Icon: LucideIcon;
  bgClass: string;
  fgClass: string;
}

/** 静态 class map：Tailwind 不能动态拼接，必须每个 kind 显式写出 utility 字符串。
 *  与 status-badge.tsx / 现有 checkout-timeline 视觉惯例一致。
 *  /15 alpha modifier 让 chip 视觉更轻；纯色调（不带 /15）会过重。 */
const KIND_META: Record<TransitionKind, KindMeta> = {
  CHECKOUT_INTERNAL:        { label: "派发",       Icon: ArrowRightFromLine, bgClass: "bg-status-in-use/15",      fgClass: "text-status-in-use-fg" },
  CHECKOUT_EXTERNAL:        { label: "出借",       Icon: Send,               bgClass: "bg-status-in-use/15",      fgClass: "text-status-in-use-fg" },
  RETURN:                   { label: "归还",       Icon: Undo2,              bgClass: "bg-status-idle/15",        fgClass: "text-status-idle-fg" },
  SEND_TO_MAINTENANCE:      { label: "送修",       Icon: Wrench,             bgClass: "bg-status-maintenance/15", fgClass: "text-status-maintenance-fg" },
  RECOVER_FROM_MAINTENANCE: { label: "维修完成",   Icon: CheckCircle2,       bgClass: "bg-status-idle/15",        fgClass: "text-status-idle-fg" },
  RETIRE:                   { label: "退役",       Icon: Moon,               bgClass: "bg-status-retired/15",     fgClass: "text-status-retired-fg" },
  REINSTATE:                { label: "重新启用",   Icon: Sun,                bgClass: "bg-status-idle/15",        fgClass: "text-status-idle-fg" },
  DISPOSE:                  { label: "处置",       Icon: Trash2,             bgClass: "bg-status-disposed/15",    fgClass: "text-status-disposed-fg" },
  RELOCATE:                 { label: "变更位置",   Icon: MapPin,             bgClass: "bg-muted",                 fgClass: "text-muted-foreground" },
  TRANSFER_HOLDER:          { label: "变更保管人", Icon: UserCog,            bgClass: "bg-muted",                 fgClass: "text-muted-foreground" },
};

function formatLine(t: TransitionRead): string {
  switch (t.kind) {
    case "CHECKOUT_INTERNAL":
      return `派发给 ${t.to_holder}` + (t.to_location ? ` · 位置 ${t.to_location}` : "");
    case "CHECKOUT_EXTERNAL":
      return `出借给 ${t.to_holder}` + (t.to_location ? ` · 位置 ${t.to_location}` : "");
    case "RETURN":
      return `归还给 ${t.to_holder ?? "无人值守"}`;
    case "SEND_TO_MAINTENANCE":
      return "送修";
    case "RECOVER_FROM_MAINTENANCE":
      return "维修完成";
    case "RETIRE":
      return "退役";
    case "REINSTATE":
      return "重新启用";
    case "DISPOSE":
      return "处置";
    case "RELOCATE":
      return `变更位置至 ${t.to_location}`;
    case "TRANSFER_HOLDER":
      return `变更保管人 ${t.from_holder ?? "无"} → ${t.to_holder}`;
    default:
      return KIND_META[t.kind]?.label ?? "未知";
  }
}

interface Props {
  assetId: string;
}

export function TransitionTimeline({ assetId }: Props) {
  const { data, isLoading, isError } = useTransitionsQuery(assetId);

  if (isLoading) return <TimelineSkeleton />;
  if (isError) return <p className="text-sm text-muted-foreground">加载流转历史失败。</p>;
  if (!data || data.length === 0) {
    return <p className="text-sm text-muted-foreground">暂无流转记录。</p>;
  }

  return (
    <ol className="space-y-3">
      {data.map((t) => {
        const meta = KIND_META[t.kind];
        const Icon = meta.Icon;
        return (
          <li
            key={t.id}
            className="rounded-lg ring-1 ring-border/60 p-3 flex items-start gap-3"
          >
            <span
              className={`inline-flex items-center justify-center size-8 rounded-full shrink-0 ${meta.bgClass} ${meta.fgClass}`}
            >
              <Icon className="size-4" aria-hidden />
            </span>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium">{formatLine(t)}</p>
              {t.note && <p className="text-xs text-muted-foreground mt-1">{t.note}</p>}
            </div>
            <time className="text-xs text-muted-foreground font-code shrink-0">
              {format(new Date(t.created_at), "yyyy-MM-dd HH:mm", { locale: zhCN })}
            </time>
          </li>
        );
      })}
    </ol>
  );
}

/** 内嵌 skeleton（沿用旧 checkout-timeline.tsx 的 inline 形态，不抽到 feedback/）。 */
function TimelineSkeleton() {
  return (
    <ol className="space-y-3">
      {Array.from({ length: 3 }).map((_, i) => (
        <li
          key={i}
          className="rounded-lg ring-1 ring-border/60 p-3 flex items-start gap-3"
        >
          <Skeleton className="size-8 rounded-full shrink-0" />
          <div className="flex-1 space-y-2">
            <Skeleton className="h-4 w-32" />
            <Skeleton className="h-3 w-48" />
          </div>
          <Skeleton className="h-3 w-24 shrink-0" />
        </li>
      ))}
    </ol>
  );
}
```

- [ ] **Step 15.2: 删除旧 checkout-timeline.tsx**

```bash
git rm frontend/src/features/assets/detail/checkout-timeline.tsx
```

- [ ] **Step 15.3: 切换 detail page import**

修改 `frontend/src/features/assets/detail/asset-detail-page.tsx`，把：

```typescript
import { CheckoutTimeline } from "./checkout-timeline";
// ...
<CheckoutTimeline assetId={asset.id} />
```

替换为：

```typescript
import { TransitionTimeline } from "./transition-timeline";
// ...
<TransitionTimeline assetId={asset.id} />
```

同时删除 detail-page 中调用 `useAssetTypesQuery` 仅为 join type_name 的逻辑（如还存在，且 detail DTO 有 type_name；C3 follow-up 留在 M3b 处理，本 task 不做）。

- [ ] **Step 15.4: 编译 + 单测验证**

Run: `pnpm --dir frontend tsc -b && pnpm --dir frontend test`
Expected: 0 错；现有 timeline/detail 单测通过（可能需修订旧测的 mock data，如 mock 的是旧 CheckoutRead）

- [ ] **Step 15.5: Commit**

```bash
git add frontend/src/features/assets/detail/transition-timeline.tsx frontend/src/features/assets/detail/asset-detail-page.tsx
git rm frontend/src/features/assets/detail/checkout-timeline.tsx
git commit -m "feat(timeline): transition-timeline 重写（10 kind icon × token 配置 + 文案模板；沿用 M2c-2 卡片堆叠形态）"
```

---

### Task 16: simplify §J/§L 顺手清理 + PR-2 验收

**Files:**
- Modify: `frontend/src/features/assets/form/build-asset-schema.ts`
- Modify: `frontend/src/features/assets/form/asset-create-form.tsx`
- Modify: `frontend/src/features/types/type-form.tsx`（同款 cast）
- Modify: `design-system/asset-hub/MASTER.md`（追加 M3a 实施期纠偏段）
- Modify: `docs/superpowers/simplify-followups.md`（标记 §J / §L 闭环）
- Modify: `docs/superpowers/followup-allocation.md`（M3a 完成回填）

- [ ] **Step 16.1.0: 先 grep 现有 build-asset-schema 代码 + cast 位置**

Run: `cat frontend/src/features/assets/form/build-asset-schema.ts`

Run: `grep -n "as unknown as Resolver\|as never" frontend/src/features/assets/form/asset-create-form.tsx frontend/src/features/assets/form/asset-edit-form.tsx frontend/src/features/types/form/type-form.tsx`

Expected: 看到双函数 `buildCreateSchema(fieldDefs)` / `buildEditSchema(fieldDefs)` 两版本（条件 `.extend`）；create-form 与 type-form 各有 `as unknown as Resolver<>` cast。

- [ ] **Step 16.1.1: 重写 build-asset-schema.ts（合一 + 显式分支）**

替换 `frontend/src/features/assets/form/build-asset-schema.ts`（保持现有 fieldDefs → zod 字段构造逻辑不变；仅修改顶层 schema 构建）：

```typescript
import { z, type ZodType } from "zod";

import { fieldDefToZod } from "./field-def-to-zod";
import type { CustomFieldDef } from "./types";

export type AssetFormMode = "create" | "edit";

/**
 * 单 builder + 显式 mode 分支（修订前是双函数 + 条件 .extend，导致 zod inference 丢 type_id 必须 cast Resolver）。
 *
 * 关键：用 `z.object({...}).extend({...})` 静态展开、不带条件分支——zod 推导可通过类型层面对 type_id 必填/可选准确反射。
 */
export function buildAssetSchema(fieldDefs: CustomFieldDef[], mode: AssetFormMode) {
  const customFields = fieldDefs.reduce<Record<string, ZodType>>((acc, def) => {
    acc[def.key] = fieldDefToZod(def);
    return acc;
  }, {});

  const baseShape = {
    name: z.string().min(1, "请输入名称"),
    serial_number: z.string().nullable().optional(),
    holder: z.string().nullable().optional(),
    location: z.string().nullable().optional(),
    notes: z.string().nullable().optional(),
    acquired_at: z.string().nullable().optional(),
    custom_data: z.object(customFields),
  };

  if (mode === "create") {
    return z.object({
      ...baseShape,
      type_id: z.string().uuid("请选择类型"),
    });
  }

  // edit：type_id 不参与表单（创建后不可改）
  return z.object(baseShape);
}

export type AssetCreateFormValues = z.infer<ReturnType<typeof buildAssetSchema>> & { type_id: string };
export type AssetEditFormValues = z.infer<ReturnType<typeof buildAssetSchema>>;
```

- [ ] **Step 16.1.2: 删 asset-create-form.tsx 的 cast**

定位 `frontend/src/features/assets/form/asset-create-form.tsx` 中类似：

```typescript
const resolver = zodResolver(schema) as unknown as Resolver<AssetCreateFormValues>;
```

替换为：

```typescript
const schema = buildAssetSchema(fieldDefs, "create");
const resolver = zodResolver(schema);  // 直接使用，无需 cast
```

`useForm<AssetCreateFormValues>({ resolver, ... })` 直接消费，不再 `as` 任何类型。

第二处 cast（如 form 内 `useWatch` 之类）按相同思路处理：let zod 推导出的类型自然流到 RHF。

- [ ] **Step 16.1.3: 删 type-form.tsx 同款 cast**

定位 `frontend/src/features/types/form/type-form.tsx` 中（M2c-4 PR-3 Task 27 引入的）：

```typescript
const resolver = zodResolver(typeSchema) as unknown as Resolver<TypeFormValues>;
```

替换为：

```typescript
const resolver = zodResolver(typeSchema);
```

如该文件还有 `build-type-schema.ts` 同款双函数 union pattern（simplify §L 提到），按相同思路合一：单 builder + mode 显式分支。具体代码与 build-asset-schema 同构。

- [ ] **Step 16.2: 跑现有 form 测试**

Run: `pnpm --dir frontend test`
Expected: 全部 PASS

- [ ] **Step 16.3: Pre-Delivery Checklist 7 项 + 红线扫描**

Run: `grep -rnE 'scale-|animate-spin|animate-pulse|backdrop-blur|bg-gradient-to' frontend/src --include='*.tsx' --include='*.ts' --include='*.css'`
Expected: 0 命中

逐项核对（手动；写入 commit message 或 PR 描述）：

- [ ] No emojis as icons（全 Lucide SVG）
- [ ] cursor-pointer on clickable elements
- [ ] Hover transitions smooth 150-300ms（`transition-colors`/`transition-shadow`，无 `transform: scale`）
- [ ] Light mode text contrast 4.5:1
- [ ] Focus states visible for keyboard
- [ ] `prefers-reduced-motion` respected（沿用 M2c-1 globals.css）
- [ ] Responsive 1024+

- [ ] **Step 16.4: playwright MCP 烟测（6 场景）**

启动 dev server：`uv run asset-hub serve start --mode dev`

用 playwright MCP 跑（每个场景产 1 张截图）：

1. 派发 → 归还 → 送修 → 维修完成 → 退役 → 重新启用 happy path（连续操作同一资产）
2. 处置（DISPOSE）：进入 RETIRED → DISPOSE 入口 → 输入"处置"解锁 → 确认 → 资产 status 变 DISPOSED + 详情页全只读
3. 列表两个 Toggle 显隐 RETIRED / DISPOSED 资产（默认隐藏；toggle 开后显示）
4. RELOCATE / TRANSFER_HOLDER 走 ⋯ 菜单（IDLE 状态下两项可见）
5. timeline 10 kind 视觉差异化（创建多个 transition 后查看 timeline，每 kind 对应正确 icon + 染色）
6. dark mode + light mode 两轮（status-disposed token 视觉验证）

烟测过程把截图贴入 PR 描述。

- [ ] **Step 16.5: 写 MASTER.md 实施期纠偏（M3a）段**

修改 `design-system/asset-hub/MASTER.md`，在末尾追加：

```markdown
## 实施期纠偏（M3a，<PR-2 合并日期>）

frontend-design skill 对 PR-2 改动做合并前对照（spec [§5.11](../../docs/superpowers/specs/2026-05-03-m3a-state-machine-design.md)）。本里程碑新增 override：

### 1. 新增 `--status-disposed` / `--status-disposed-fg` OKLCH token pair
DISPOSED（已处置）状态的 token，完全去色相纯灰（chroma=0），与 RETIRED（保留微弱蓝色相）区分。light/dark 两套 + `@theme` 映射。

### 2. Toggle chip 模式（filter 区使用 status token 染色的 Toggle，非普通 checkbox）
列表 filter 区 "已退役" / "已处置" 两个独立 Toggle chip，按 status token 染色（off muted / on status-X/15 + status-X-fg + status-X/30 border）。视觉与 status pill 体系延续。

### 3. DisposeAlertDialog 二次确认形态
DISPOSE 终态不可逆，dialog 内输入"处置"二字解锁主按钮（参考 `delete-asset-alert.tsx` pattern）。destructive 红色按钮 + Trash2 icon。

### 4. timeline 10 kind icon × token 配置表
`transition-timeline.tsx` 的 KIND_META 表显式列 10 kind 对应的 lucide icon + status token + 文案。CHECKOUT/RETURN/SEND_TO_MAINTENANCE/RECOVER/RETIRE/REINSTATE/DISPOSE 走对应 status 色调；RELOCATE/TRANSFER_HOLDER 走 muted 中性。沿用 M2c-2 卡片堆叠形态，§14.8 高级视觉留 M3d。

### 5. RETIRED Icon 从 `MinusCircle` 改 `Moon`
"休眠待复活"语义，与 RETIRE transition kind 在 timeline 的 icon 一致；M2c-1 旧 MinusCircle 弃用。

### Pre-Delivery Checklist（M3a PR-2 验证）

- [x] No emojis as icons（全 Lucide SVG）
- [x] cursor-pointer on clickable elements
- [x] Hover transitions smooth 150-300ms
- [x] Light mode text contrast 4.5:1
- [x] Focus states visible for keyboard
- [x] `prefers-reduced-motion` respected
- [x] Responsive 1024+

### 红线扫描结果

`grep -rnE 'scale-|animate-spin|animate-pulse|backdrop-blur|bg-gradient-to'` 在 PR-2 新增/修改文件内：**0 命中**。
```

填入实际 PR-2 合并日期。

- [ ] **Step 16.6: 更新 simplify-followups + followup-allocation**

修改 `docs/superpowers/simplify-followups.md`：

- §C C1 状态改为 ✅ 闭环（落地于 M3a PR-1 commit ref）
- §J / §L / §M 状态改为 ✅ 闭环（落地于 M3a PR-2 commit ref）
- §A A3（CheckoutDialog/ReturnDialog 合并）状态：备注"M3a 时机已到但决议推迟 M4 UI 打磨期，避免落入模板脸"

修改 `docs/superpowers/followup-allocation.md` §M3 表格：

- C1 / §J / §L / smoketest B1 / §14.3 / §14.6 / §14.7 / §14.1 全部标 ✅ 落地于 M3a
- A3 改"推迟 M4"

- [ ] **Step 16.7: PR-2 push + 创建 PR**

```bash
uv run pytest tests/  # 确保 PR-1 已合并的测试仍 100% 绿
pnpm --dir frontend tsc -b  # 0 错
pnpm --dir frontend lint
pnpm --dir frontend test  # 前端单测全绿

git log --oneline main..HEAD
git push -u origin <branch>

gh pr create --title "M3a PR-2: 前端切换 + UX 完整" --body "..."
```

PR 描述包含：
- M3a spec + PR-1 链接
- PR-2 范围（task 1-16）
- 测试结果（pytest 全绿 + tsc 0 错 + 前端单测 + 红线扫描 0 命中）
- playwright MCP 烟测 6 场景截图
- MASTER override 5 项 + Pre-Delivery 7 项 全 ✓
- simplify §C1 / §J / §L / smoketest B1 / §14.3 / §14.6 / §14.7 / §14.1 闭环 commit ref
- A3 推迟 M4 备注

- [ ] **Step 16.8: PR-2 合并 → M3a 完工**

PR-2 通过 review + 合并到 main 后，M3a 子里程碑完工。下一步进入 M3b 看板 brainstorm。

---

## Self-Review

**Spec coverage 核对**（spec §5 子章节 → 任务对应）：

- §5.1 design-system token → Task 1
- §5.2 status-labels → Task 2
- §5.3 列表 Toggle chip → Task 14
- §5.4 6/7 dialog → Task 6-12
- §5.5 ⋯ 菜单 → Task 5 + Task 13
- §5.6 timeline → Task 15
- §5.7 hooks / query keys → Task 3
- §5.8 simplify §J/§L → Task 16
- §5.9 反 AI-slop 红线 → Task 16 红线扫描
- §5.10 shadcn Toggle 审查 + 响应式 → Task 6 / Task 14
- §5.11 playwright MCP 烟测 + Pre-Delivery + MASTER override → Task 16

**类型一致性**：`TransitionKind` 在 hooks（Task 3）/ available-transitions（Task 5）/ 各 dialog（Task 6-12）/ timeline（Task 15）一致从 `components["schemas"]["TransitionKind"]` 取，命名稳定。

**未引入新决策**：所有任务严格执行 spec §5 已拍板内容，未自主扩展范围。
