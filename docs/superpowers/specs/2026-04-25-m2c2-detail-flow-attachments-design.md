# M2c-2 · 资产详情 + 流转 + 附件查看 设计文档

- **日期**：2026-04-25
- **里程碑**：M2c 第 2 子项（详情 + 流转 + 附件查看）
- **状态**：初稿，待实施
- **作者**：conghaoyangbobby@gmail.com（与 Claude 协同 brainstorm）
- **承接**：[`2026-04-15-asset-hub-design.md`](./2026-04-15-asset-hub-design.md) §7.1 / [`2026-04-24-m2c1-frontend-foundation-and-list-design.md`](./2026-04-24-m2c1-frontend-foundation-and-list-design.md) §0 表

## 0. 导读

本文档是 **M2c 子里程碑拆分后的第 2 份 spec**。

| 子里程碑 | 范围 | spec |
| --- | --- | --- |
| M2c-1 · 地基 + 列表 | 前端工具链、数据层、主题、布局壳、资产列表页 | [✓ 已交付](./2026-04-24-m2c1-frontend-foundation-and-list-design.md) |
| **M2c-2 · 详情 + 流转 + 附件查看**（本文） | 详情页 + 派发/归还对话框 + 流转时间线 + 附件查看 + 删除 | 本文 |
| M2c-3 · 表单 + 附件上传 | 登记/编辑表单（动态 `custom_fields`）+ 附件上传 UI + Vitest + RHF + Zod | 未写 |

M3（看板 + 导出 + 后端字段补齐 + 派出类型扩展）、M4（审美打磨 + 命令面板 + 响应式）均在 M2c 完结之后再动。

## 1. 目标与非目标

### 1.1 目标

把 M2c-1 列表页"行点击 → 404 占位"接通到一个完整可用的资产详情页，并在该页落地三类**只读为主、流转为辅**的能力：

- 路由 `/assets/:id`：UUID 参数 + 三态壳（loading / 404 / error / ok）+ 标准化错误处理
- 详情页主体（单列 stacked，max-width ≈960px 居中）：
  - **AssetHeader**：名 + 类型 + 状态 + 单主 CTA（动词跟随 status：IDLE→派发 / IN_USE→归还 / 其他→disabled tooltip）
  - **GeneralFields**：通用字段 `<dl>` 列表
  - **CustomFields**：按 `AssetType.custom_fields` schema 完整格式化的类型字段
  - **AttachmentGrid**：3-4 列宫格缩略图，点击进 lightbox
  - **CheckoutTimeline**：纵向时间线（2 节点形态 + "进行中" 文字标）
- 三个浮层组件：
  - **CheckoutDialog**：派发表单（holder 必填、location/note 可选）
  - **ReturnDialog**：归还表单（note 可选；顶部展示当前持有上下文供二次确认）
  - **AttachmentLightbox**：Radix Dialog + 图/非图分支 + 内嵌 AlertDialog 二次确认删除
- 6 个新 hook：`useAssetDetailQuery / useCheckoutHistoryQuery / useAttachmentsQuery / useCheckoutMutation / useReturnMutation / useDeleteAttachmentMutation`
- 列表页接通：`AssetsTable` 的行点击 href 从 `#` 改为 `/assets/${id}`；⋯ 菜单的"派发/归还"两项解除 disabled 并接通到 Dialog；"编辑/删除"维持 disabled 文案改为"M2c-3 开放"

### 1.2 非目标（明确推走）

| 非目标 | 去处 |
| --- | --- |
| 编辑资产 UI（任何字段的写） | M2c-3 |
| 删除资产 UI | M2c-3 |
| 附件**上传** UI | M2c-3 |
| 动态 `custom_fields` 表单渲染（登记/编辑场景） | M2c-3 |
| Vitest + RHF + Zod 引入 | M2c-3 |
| 后端 `Asset.asset_code` / `Asset.type_name` / `Asset.current_checkout_id` 字段补齐 | M3 |
| `AssetType.code_prefix` 字段 | M3 |
| 派出类型扩展（"向外出借"、split-button、`CheckoutRecord.kind`） | M3 |
| 流转 timeline 视觉重构（时间渐隐 / 类型染色 / 超长预警） | M3 |
| 看板 / 导出 / 类型管理 UI | M3 |
| 命令面板、响应式 polish、微动效 polish | M4 |
| i18n 脚手架 | 直接硬编码中文 |

**后端零改动**——M2c-2 与 M2c-1 同款节奏，所有上游字段缺口推 M3 统一补，详见 §10。

## 2. 关键决策（已定）

每条决策在 brainstorm 阶段逐个对齐，此处定型。

| ID | 决策 | 选项 | 理由 |
| --- | --- | --- | --- |
| D1 | 编辑范围 | **纯只读 + 流转操作**（派发/归还/附件删除）；编辑/删除资产保留 M2c-3 | 与 M2c-1 §5.4 mutation 失效表的"按钮接线分配"自洽；保留 M2c-3 表单里程碑完整性 |
| D2 | 详情页布局 | **单列 stacked**，max-width ≈960px 居中 | 数据密度不高 + 单用户 + 低频访问，线性阅读最直接；不引入 sidebar / Tab 等结构性复杂度 |
| D3 | "当前派发"数据来源 | **纯前端推导**：详情页并发 `GET asset` + `GET history`，从 history 找 `returned_at === null` 的唯一一条 | 详情页本就要 history，无额外请求成本；后端不动，与 M2c-1 节奏一致 |
| D4 | Header CTA 形态 | **单主 CTA 动词跟随 status**：IDLE→"派发"、IN_USE→"归还"、其他→disabled+tooltip | 动词跟随状态是库存/资产系统主流模式；预留 M3 split-button 升级路径（详见 §10） |
| D5 | 流转时间线视觉 | **纵向 timeline**：左线 + 圆点节点 + 右侧轻卡片；当前派发节点实心 CTA 色 + 卡片右上角"进行中"小标 | 流转的"时间事件"本质契合 timeline 隐喻；本里程碑 2 节点形态 + 1 文字标的最简版（M3 重构详见 §10） |
| D6 | 附件查看交互 | **3-4 列宫格缩略图 + Radix Dialog lightbox + AlertDialog 二次确认删除** | lightbox 是照片查看器行业标准；Dialog 内可同时承载图与非图；AlertDialog 对"不可恢复删除"是 UX 正道 |
| D7 | `custom_data` 渲染策略 | **schema-driven 完整格式化**：用 `AssetType.custom_fields` 的 label + type 映射格式化 value；缺失数据兜底 "—"；未知字段 italic 不静默隐藏 | M2c-1 已 cache schema（`staleTime: Infinity`），格式化零网络成本；本项目数据质量依赖单用户 + Agent，少数格式化分支完全可控 |
| D8 | Dialog 表单实现层 | **纯 React state + 手工校验** | M2c-3 是 RHF+Zod+Vitest 完整引入点，提前装库无测试抓手是空跑；3 字段 dialog 用 RHF 收益微乎其微；M2c-3 plan 单开 Task 迁移（约半天，详见 §10） |

## 3. 设计系统 baseline

### 3.1 baseline 继承（不重跑 ui-ux-pro-max）

M2c-1 已生成全套设计系统产物，本里程碑**完整继承、不修改**：

- `design-system/asset-hub/MASTER.md` —— 全局权威 tokens（色板 / 字体 / 间距 / 阴影 / Button-Card-Input-Modal 规格 / 反模式 / Pre-Delivery Checklist）
- `design-system/asset-hub/pages/assets-list.md` —— 列表页 override（与 M2c-2 无关，原样保留）
- `frontend/src/styles/globals.css` —— CSS variable 与 4 态状态色 token；M2c-2 **不新增任何变量**

### 3.2 是否需要 page override

**不生成** `design-system/asset-hub/pages/assets-detail.md`：

- 详情页与 MASTER 的 baseline（Data-Dense Dashboard）方向一致
- 单实体页不需要 list 的"密度优化"override
- 任何偏离 MASTER 的实施细节，按 M2c-1 同款做法在 §3.4 的"实施期纠偏"环节回写到 MASTER 末尾

### 3.3 frontend-design skill 在本里程碑的位置（与 M2c-1 §3.4 同款 3 闸门）

| 闸门 | 时机 | 内容 |
| --- | --- | --- |
| ① | spec 阶段（**当前文档**） | §3.5 审美纲领明确写出 M2c-2 各 Task 必须满足的红线；plan 阶段每个 UI Task 末尾"§3.5 约束引用"栏对齐 |
| ② | 实施期 Task 粒度 | 每完成一个 UI 组件 Task，跑一次 §3.5 红线扫描（grep `scale-` / `animate-spin` / `backdrop-blur` / `gradient`）；不通过当 Task 立即修复 |
| ③ | 合并前最终审查 | 跑一遍附录 A 烟测（12 项）+ MASTER `Pre-Delivery Checklist` 7 项 + frontend-design skill 走一轮 |
| ④ | 纠偏回写 | M2c-2 实施期发现的上游缺口、临时权宜、偏离 MASTER 的细节，回写到 `design-system/asset-hub/MASTER.md` 末尾"实施期纠偏（M2c-2）"区块 |

### 3.4 §3.5 审美纲领（M2c-2 落地清单）

> **基线不变**：色板 / 字体 / 间距 / radius / 状态色全部继承 M2c-1 `globals.css`，不新增 CSS variable。

| § | 条目 | M2c-2 落地点 |
| --- | --- | --- |
| §3.5.1 | fewer-but-better（密度克制） | 单列 + max-width 960px + section 之间 `space-y-8`；不用 Card 装饰；GeneralFields / CustomFields 用 `<dl>` 不用表格 |
| §3.5.2 | 字体（Fira Sans body / Fira Code 编号） | SN / UUID / asset_id 显示用 `font-code`；其余 body 默认；timeline 时间戳用 `font-code` |
| §3.5.3 | 状态色（4 态语义） | StatusBadge 直接复用；timeline 当前节点用 `--status-active` 同源；CTA disabled 文案的 tooltip 用 muted-foreground |
| §3.5.4 | radius=0.375rem | shadcn Dialog / AlertDialog / DropdownMenu 自动跟 token |
| §3.5.5 | Motion 三时刻 | **时刻 1（页面入场）：详情页不做 stagger**——单实体页"摇一下"反而打扰，应静态稳重；时刻 2（交互反馈）：CTA 色变 150-300ms / 缩略图 hover ring 色变 / Dialog 默认 Radix scale-in；时刻 3（状态切换）：`prefers-reduced-motion` 全降级 |
| §3.5.6 | 红线（禁 transform scale / animate-spin / backdrop-blur / 多层 shadow / 渐变背景） | 缩略图 hover 仅 `ring-2 ring-primary/40`；Dialog overlay `bg-black/50` 不 blur；mutation pending 不显式 spinner（按钮文字切 "派发中…"）；timeline 不用 shadow |
| §3.5.7 | shadcn variant 审查 | 本里程碑新增 `dialog / alert-dialog` 两个 shadcn 组件（separator 因放弃使用不再引入）；引入即审：`Dialog.Overlay` 默认 `bg-black/80` 改 `bg-black/50` 不 blur；移除 Next 残留 `"use client"` 指令 |

### 3.4.1 MASTER override（显式）

以下条目对 MASTER 的默认建议做显式覆盖；实施期纠偏回写（§3.3 闸门 ④）时一并同步到 `design-system/asset-hub/MASTER.md` 末尾"实施期纠偏（M2c-2）"区块：

| MASTER 条目 | M2c-2 覆盖 | 理由 |
| --- | --- | --- |
| `Key Effects: data loading spinners` | mutation pending 改用 Button 文字切换（"派发中…" / "归还中…" / "删除中…"）；query loading 用骨架（`DetailSkeleton` / `GridSkeleton` / `TimelineSkeleton`） | 转圈 spinner 是 AI-slop 重灾区；文字切换 + 骨架更语义，与 §3.5.6 禁 `animate-spin` 红线自洽 |
| `Key Effects: chart zoom on click` | N/A | M2c-2 无 chart（M2c-1 同理，已记录于 MASTER 末尾） |
| `Modal: backdrop-filter: blur(4px)` | Dialog/AlertDialog overlay 改 `bg-black/50` 不带 blur | §3.5.6 禁 backdrop-blur；glassmorphism 是 overused AI 审美 |
| `Card: box-shadow + translateY on hover` | M2c-2 不用 Card 装饰区块；timeline 卡片 `ring-1 ring-border/60` 无 shadow、无 hover 位移 | §3.5.1 fewer-but-better；hover 位移会造成 layout shift（MASTER anti-pattern #3 自己也禁止） |

## 4. 架构与文件结构

### 4.1 架构

```
路由层      │ /assets/:id  ← M2c-1 行点击接通
  ↓
页面层      │ AssetDetailPage（三态壳：loading/404/error/ok）
  ↓
业务区块层  │ AssetHeader · GeneralFields · CustomFields
            │ AttachmentGrid · CheckoutTimeline
            │ CheckoutDialog · ReturnDialog · AttachmentLightbox
            │ NotFoundPanel
  ↓
数据/hook 层 │ M2c-1 已建 + M2c-2 新增 6 个 hook
  ↓
client 层   │ openapi-fetch（M2c-1 已建，零改动）
  ↓
后端        │ FastAPI（零改动）
```

### 4.2 文件结构（新增/修改）

```
frontend/src/
├── routes/
│   ├── assets.$id.tsx                   # 新：TanStack Router file-based detail 路由
│   └── index.tsx                        # 修：行点击 href 从 # 改为 /assets/${id}
├── api/
│   ├── query-keys.ts                    # 修：新增 detail / history / attachments key factory
│   └── hooks/
│       ├── assets.ts                    # 修：新增 useAssetDetailQuery
│       ├── checkouts.ts                 # 新：history query + checkout/return mutation
│       └── attachments.ts               # 新：list query + delete mutation
├── features/assets/
│   ├── detail/
│   │   ├── asset-detail-page.tsx        # 新：页面组装容器（被 routes/assets.$id.tsx 调用）
│   │   ├── asset-header.tsx             # 新：名 + 类型 + 状态 + CTA
│   │   ├── current-checkout.ts          # 新：deriveCurrentCheckout 纯函数
│   │   ├── general-fields.tsx           # 新
│   │   ├── custom-fields.tsx            # 新
│   │   ├── custom-field-formatter.ts    # 新：按 AssetType field def + value 格式化
│   │   ├── attachment-grid.tsx          # 新
│   │   ├── attachment-lightbox.tsx      # 新：Radix Dialog + 图/非图分支
│   │   ├── checkout-timeline.tsx        # 新：纵向 timeline
│   │   ├── checkout-dialog.tsx          # 新
│   │   ├── return-dialog.tsx            # 新
│   │   ├── checkout-actions.ts          # 新：CTA 动词常量（M3 派出类型扩展落点）
│   │   └── not-found-panel.tsx          # 新
│   └── list/
│       └── assets-table.tsx             # 修：行点击接通 + ⋯ 菜单派发/归还接线
└── components/ui/                       # shadcn 按需补：dialog, alert-dialog, separator
```

**统计**：新增 16 个文件（routes 1 + hooks 2 + features/assets/detail 13）、修改 4 个文件（query-keys + hooks/assets + routes/index + list/assets-table）、shadcn add 2 个组件（`dialog` + `alert-dialog`；放弃 `separator`——§7.1 决定不用 `<Separator />`）。不新建 `lib/` 工具（格式化器独立放 detail 目录，符合 M2c-1 的"feature 自治"原则）。

### 4.3 依赖

**不新增任何 npm 依赖**。所需能力 100% 来自 M2c-1 已装：

- `@tanstack/react-query`（query / mutation）
- `@tanstack/react-router`（file-based route + UUID params 校验）
- `openapi-fetch` + 生成的 `schema.d.ts`
- `lucide-react`（新用 icon：`Trash2 / Download / FileText / FileImage / File / Clock / Check / X`）
- `sonner`（Toast）
- `date-fns`（M2c-1 已装，timeline 时间相对化用 `formatDistanceToNow`、custom_field date 用 `format(parseISO, 'yyyy-MM-dd')`）

shadcn `dialog / alert-dialog` 通过 `pnpm dlx shadcn@latest add` 引入，引入后必须在同 PR 内审查（§3.5.7）。

## 5. 数据层

### 5.1 queryKey 扩展

承接 M2c-1 `api/query-keys.ts`：

```ts
export const qk = {
  assets: {
    all: ['assets'] as const,
    list: (search: AssetsSearch) => [...qk.assets.all, 'list', search] as const,
    detail: (id: string) => [...qk.assets.all, 'detail', id] as const,        // 新
    history: (id: string) => [...qk.assets.all, id, 'history'] as const,      // 新
  },
  assetTypes: {
    all: ['asset-types'] as const,
  },
  attachments: {
    byAsset: (assetId: string) => ['attachments', 'byAsset', assetId] as const,  // 新
  },
} as const
```

`history` 不放在 `qk.assets.detail(id)` 子节点而是独立分支，是因为 `qk.assets.all` 失效时需要同时把 history 失效（checkout 改写了 history），独立分支让失效语义更显式。

### 5.2 hooks 一览

| Hook | 文件 | 类型 | HTTP | 失效依赖 |
| --- | --- | --- | --- | --- |
| `useAssetDetailQuery(id)` | `hooks/assets.ts` | Query | `GET /api/assets/:id` | — |
| `useCheckoutHistoryQuery(id)` | `hooks/checkouts.ts` | Query | `GET /api/assets/:id/history` | — |
| `useAttachmentsQuery(assetId)` | `hooks/attachments.ts` | Query | `GET /api/assets/:id/attachments` | — |
| `useCheckoutMutation()` | `hooks/checkouts.ts` | Mutation | `POST /api/assets/:id/checkout` | 见 §5.3 |
| `useReturnMutation()` | `hooks/checkouts.ts` | Mutation | `POST /api/assets/:id/return` | 见 §5.3 |
| `useDeleteAttachmentMutation()` | `hooks/attachments.ts` | Mutation | `DELETE /api/attachments/:id` | 见 §5.3 |

### 5.3 mutation 失效策略（承接 M2c-1 §5.4）

| Mutation | 失效 | 理由 |
| --- | --- | --- |
| `checkout(assetId, body)` | `qk.assets.all` + `qk.assets.detail(assetId)` + `qk.assets.history(assetId)` | 三处同时变化：list 中 status；detail 中 status/holder；history 多一条进行中 |
| `return_(assetId, body)` | 同上三项 | 归还也让 status / history 变 |
| `deleteAttachment(attachmentId, assetId)` | 仅 `qk.attachments.byAsset(assetId)` | 不影响 asset / history；mutationFn 入参需要带 assetId 才能精确失效 |

注意 `useDeleteAttachmentMutation` 的 mutationFn 接受 `{ attachmentId, assetId }` 而非仅 `attachmentId`——TanStack Query 失效需要知道 assetId 才能定位 queryKey。

### 5.4 当前派发派生（纯函数）

`features/assets/detail/current-checkout.ts`：

```ts
import type { components } from '@/api/generated/schema'

type CheckoutRead = components['schemas']['CheckoutRead']

/**
 * 从流转 history 中找出"当前进行中"的派发记录。
 *
 * 不变量（service 层保证）：同一资产同一时刻最多 1 条 returned_at === null。
 */
export function deriveCurrentCheckout(history: CheckoutRead[]): CheckoutRead | null {
  return history.find((c) => c.returned_at === null) ?? null
}
```

设计为纯函数是为了：
- 单元测对象（M2c-3 引入 Vitest 后第一批可测）
- 不依赖任何 React 上下文，可在 ReturnDialog 顶部预填上下文时复用
- 降级路径：若 history 拉取失败但 asset 拿到了，可用 `null` 兜底，UI 呈现"无法确认是否派发中"的中间态

### 5.5 数据并发模式

`AssetDetailPage` 内三个 query 直接并行声明（React Query 自动并发），不用 `useQueries` 包裹除非要等全部 settled：

```tsx
const assetQuery = useAssetDetailQuery(id)
const historyQuery = useCheckoutHistoryQuery(id)
const attachmentsQuery = useAttachmentsQuery(id)
```

各区块独立 loading/error 渲染：
- `assetQuery` 是页面级 — 它失败页面进入 ErrorState；它 404 进入 NotFoundPanel
- `historyQuery` / `attachmentsQuery` 失败仅该区块替换为 mini ErrorState，不污染其他区块
- 区块级"loading 不阻塞"：asset 拿到就先渲染 Header/字段，history/attachments 各自 skeleton

## 6. 路由 + 参数校验

### 6.1 文件位置

`frontend/src/routes/assets.$id.tsx`（TanStack Router file-based 命名约定，`$id` 是动态段）

### 6.2 UUID 校验

```ts
import { createFileRoute } from '@tanstack/react-router'
import { z } from 'zod'

export const Route = createFileRoute('/assets/$id')({
  parseParams: ({ id }) => ({ id: z.string().uuid().parse(id) }),
  // parse 失败 → throw → 落到 errorComponent 或全局 ErrorBoundary
  component: AssetDetailPage,
  errorComponent: NotFoundPanel,  // UUID 格式错也归类为"找不到"
})
```

UUID 解析失败的 UX 含义是"链接坏了 / 用户手输错"，归类为 NotFoundPanel 而非 ErrorState，对用户更友好。

### 6.3 与 list 页的接通

`features/assets/list/assets-table.tsx` 的行点击 from M2c-1：
```diff
- <tr onClick={...} className="cursor-pointer">
+ <tr onClick={() => navigate({ to: '/assets/$id', params: { id: row.id } })}
+     className="cursor-pointer">
```

⋯ 菜单的 4 项：
- "派发（M2c-2 开放）"  → 解除 disabled，点击 `setCheckoutDialogState({ open: true, assetId: row.id })`
- "归还（M2c-2 开放）"  → 解除 disabled，依据 `row.status === 'IN_USE'` 决定 enable
- "编辑（M2c-3 开放）"  → 维持 disabled，文案不变
- "删除（M2c-3 开放）"  → 维持 disabled，文案不变

注意"派发/归还"在列表页的 ⋯ 菜单触发的 Dialog 也是 M2c-2 的 `CheckoutDialog`/`ReturnDialog` 同款组件——为此 Dialog 组件需要支持 `assetId` prop 而非依赖 detail page 上下文。

## 7. 页面结构

### 7.1 AssetDetailPage 三态壳

```
routes/assets.$id.tsx
└─ AssetDetailPage (features/assets/detail/asset-detail-page.tsx)
   │
   ├─ <title>{asset?.name ?? '加载中…'} · asset-hub</title>
   │
   ├─ if assetQuery.isLoading        → <DetailSkeleton />
   ├─ if assetQuery.error.status===404 → <NotFoundPanel />
   ├─ if assetQuery.isError          → <ErrorState onRetry={assetQuery.refetch} />
   │
   └─ if assetQuery.data:
      <main className="mx-auto max-w-[960px] py-8 px-4 space-y-10">
        <AssetHeader ... />
        <GeneralFields ... />
        <CustomFields ... />
        <AttachmentGrid ... />
        <CheckoutTimeline ... />
        <浮层们 ... />
      </main>

**分隔策略**：区块间仅靠 `space-y-10` 节律 + 各 section 内 `<h2>` 语义标题分区，**不用 `<Separator />`**。理由：
- 单实体详情页视觉焦点在"信息密度与层级"，横线会过度"隔间化"、让页面显得零散
- 设计节制（fewer-but-better）是 §3.5.1 的直接体现
- 垂直节律 `space-y-10` ≈ 40px 配合 `<h2 text-lg font-medium>` 足够形成视觉分段
```

`<DetailSkeleton>` 是新组件（不复用 M2c-1 的 SkeletonRow，那是表格行用的）：模拟单列布局——顶部一条粗线（Header）、中间几行短线（字段）、底部一组方块（附件）+ 一组短线（timeline）。

### 7.2 AssetHeader

```
<header className="flex items-start justify-between gap-4">
  <div className="space-y-1">
    <Link to="/" className="text-sm text-muted-foreground">← 返回列表</Link>
    <h1 className="text-2xl font-semibold">{asset.name}</h1>
    <div className="flex items-center gap-3">
      <span className="text-sm text-muted-foreground">{typeName ?? '未知类型'}</span>
      <StatusBadge status={asset.status} />
    </div>
    {asset.status === 'IN_USE' && currentCheckout && (
      <p className="text-sm text-muted-foreground">
        当前派发给 · <span className="text-foreground">{currentCheckout.holder}</span>
        {currentCheckout.location && <> · {currentCheckout.location}</>}
        {' · 自 '}<time className="font-code">{formatDate(currentCheckout.checked_out_at)}</time>
      </p>
    )}
  </div>
  <CtaButton status={asset.status} onCheckout={...} onReturn={...} />
</header>
```

**返回按钮**：基础版直接 `<Link to="/">`，不保留 search params。M4 polish 时若有"回到原筛选"诉求再补（用 TanStack Router 的 `useRouter().history` 反查或手动维护 lastListSearch atom）。

**CtaButton** 行为表：

| `asset.status` | 渲染 | 点击行为 |
| --- | --- | --- |
| `IDLE` | `<Button>派发</Button>`（primary） | 打开 CheckoutDialog |
| `IN_USE` | `<Button>归还</Button>`（primary） | 打开 ReturnDialog |
| `MAINTENANCE` | `<Button disabled>派发</Button>` + Tooltip "维护中的资产不可派发" | — |
| `RETIRED` | `<Button disabled>派发</Button>` + Tooltip "已退役的资产不可派发" | — |

CTA 动词字符串从 `checkout-actions.ts` 导出：
```ts
export const CHECKOUT_VERB = '派发'  // M3 扩展时变成 [{ key, verb, ... }] 数组
export const RETURN_VERB = '归还'
```

### 7.3 GeneralFields

`<dl>` 渲染，左列 label（`muted-foreground` + `text-sm`）/ 右列 value（默认 foreground）：

| label | value |
| --- | --- |
| 编号（SN） | `asset.serial_number ?? '—'`，`font-code` |
| 资产 ID | `asset.id`，`font-code` + 带"复制"按钮（Lucide `Copy`），点击 `navigator.clipboard.writeText(id)` + Toast |
| 类型 | `typeName`（来自 `useAssetTypesQuery` 的客户端 join，与 M2c-1 列表页同款） |
| 当前持有人 | `asset.holder ?? '—'`（与 Header 的 currentCheckout.holder 区分语义：这里是 Asset 表上"快照"字段） |
| 当前位置 | `asset.location ?? '—'` |
| 备注 | `asset.notes ?? '—'`，超长按 `whitespace-pre-wrap` 保留换行 |
| 创建时间 | `formatDate(asset.created_at)`，`font-code` |
| 最后更新 | `formatDate(asset.updated_at)`，`font-code` |

每行 `py-3` + `border-b border-border/50` 弱分隔线。

### 7.4 CustomFields + 格式化器

`<dl>` 同 GeneralFields，但字段定义来自 `assetType.custom_fields`（schema 数组）+ `asset.custom_data`（dict）。

```tsx
function CustomFields({ asset, assetType }) {
  if (!assetType.custom_fields.length) return null  // §1.1 子决策：空类型字段整块不渲染

  const knownKeys = new Set(assetType.custom_fields.map(f => f.key))
  const unknownEntries = Object.entries(asset.custom_data).filter(([k]) => !knownKeys.has(k))

  return (
    <section>
      <h2 className="text-lg font-medium mb-3">类型字段</h2>
      <dl>
        {assetType.custom_fields.map(def => (
          <Row key={def.key} label={def.label} value={
            def.key in asset.custom_data
              ? formatCustomFieldValue(def, asset.custom_data[def.key])
              : <span className="text-muted-foreground">—</span>
          } />
        ))}
        {unknownEntries.map(([key, value]) => (
          <Row key={key}
               label={<span className="italic">{key} <small className="text-muted-foreground">（未知字段）</small></span>}
               value={String(value)} />
        ))}
      </dl>
    </section>
  )
}
```

**`formatCustomFieldValue(def, value)` 分支**（位于 `custom-field-formatter.ts`）：

| `def.type` | 格式化 |
| --- | --- |
| `string` / `text` | 原样字符串；`text` 加 `whitespace-pre-wrap` |
| `int` / `float` | `new Intl.NumberFormat('zh-CN').format(value)`（千分位） |
| `bool` | `true` → `<Check className="text-status-active" />`；`false` → `<X className="text-muted-foreground" />` |
| `date` | `format(parseISO(value), 'yyyy-MM-dd')`（date-fns） |
| `enum` | 直接显示 value（`options` 已是人可读标签，不再 lookup） |

边界处理：
- value 为 `null` / `undefined` → "—"
- value 类型与 def.type 不符（脏数据）→ try/catch 兜底显示 `String(value)` + small `（数据格式异常）`（避免 throw 触发 ErrorBoundary）

### 7.5 AttachmentGrid + Lightbox

#### AttachmentGrid

```tsx
<section>
  <h2 className="text-lg font-medium mb-3">附件</h2>
  {attachmentsQuery.isLoading ? <GridSkeleton /> :
   attachmentsQuery.isError ? <ErrorState compact onRetry={...} /> :
   attachments.length === 0 ? <EmptyState
     icon={<Paperclip />}
     title="暂无附件"
     description="通过登记流程或 asset-hub attachment add CLI 上传"
   /> :
   <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
     {attachments.map(att => (
       <button
         key={att.id}
         onClick={() => setLightboxState({ open: true, attachment: att })}
         className="aspect-square ring-1 ring-border hover:ring-2 hover:ring-primary/40 rounded-md overflow-hidden cursor-pointer transition-shadow"
       >
         {att.mime_type.startsWith('image/')
           ? <img src={`/api/attachments/${att.id}/content`} className="object-cover w-full h-full" />
           : <KindIcon mime={att.mime_type} filename={att.original_name} />}
       </button>
     ))}
   </div>
  }
</section>
```

`KindIcon` 选择：`application/pdf` → `FileText`；`image/*` → `FileImage`（兜底，正常路径走 `<img>`）；其他 → `File`。

#### AttachmentLightbox

```
<Dialog>
  <DialogContent className="max-w-[90vw] max-h-[90vh] p-0 overflow-hidden">
    <DialogHeader className="absolute top-2 right-2 z-10 flex flex-row gap-2">
      <Button variant="ghost" size="icon" onClick={() => window.open(downloadUrl, '_blank')}>
        <Download />
      </Button>
      <Button variant="ghost" size="icon" onClick={() => setAlertDialogOpen(true)}>
        <Trash2 className="text-destructive" />
      </Button>
      <DialogClose asChild><Button variant="ghost" size="icon"><X /></Button></DialogClose>
    </DialogHeader>

    {att.mime_type.startsWith('image/')
      ? <img src={contentUrl} className="object-contain max-w-full max-h-[90vh]" />
      : <MetadataPanel attachment={att} />  /* 文件名/大小/mime/上传时间 + "在新窗口打开"按钮 */
    }
  </DialogContent>

  <AlertDialog open={alertDialogOpen}>...</AlertDialog>
</Dialog>
```

**Dialog overlay 必须改 `bg-black/50` 不带 blur**（§3.5.7 红线）。

### 7.6 CheckoutTimeline

```
<section>
  <h2 className="text-lg font-medium mb-3">流转记录</h2>
  {historyQuery.isLoading ? <TimelineSkeleton /> :
   historyQuery.isError ? <ErrorState compact onRetry={...} /> :
   history.length === 0 ? <EmptyState title="暂无流转记录" /> :
   <ol className="relative pl-6">
     <div className="absolute left-2 top-2 bottom-2 w-px bg-border" />
     {history.map(c => (
       <li key={c.id} className="relative pb-6 last:pb-0">
         <Node isCurrent={c.returned_at === null} />
         <Card checkout={c} />
       </li>
     ))}
   </ol>
  }
</section>
```

**Node 视觉**：
- 当前派发（`returned_at === null`）：实心圆点，`bg-status-active` (= CTA amber)，`absolute left-1 top-1.5 w-3 h-3 rounded-full`
- 历史派发：空心圆点，`border-2 border-muted-foreground bg-background`

**Card 视觉**：
- 容器：`rounded-md ring-1 ring-border/60 p-3 space-y-1`，无 shadow
- 第一行：`<span className="font-medium">{c.holder}</span>` + 若 `c.location` 跟空格分隔显示
- 第二行：`<time className="font-code text-sm">{formatDate(c.checked_out_at)} → {c.returned_at ? formatDate(c.returned_at) : <Badge variant="outline" className="text-status-active">进行中</Badge>}</time>`
- 第三行（条件）：`c.checkout_note` 渲染为小字 muted "派发备注：..."；`c.return_note` 渲染为 "归还备注：..."（仅已归还时显示）

**M3 重构清单**（§10 详述）：本里程碑只做 2 节点形态 + 1 文字标的最简版。

### 7.7 CheckoutDialog / ReturnDialog

#### CheckoutDialog

```tsx
function CheckoutDialog({ open, onOpenChange, assetId }) {
  const [holder, setHolder] = useState('')
  const [location, setLocation] = useState('')
  const [note, setNote] = useState('')
  const [holderError, setHolderError] = useState('')
  const [submitError, setSubmitError] = useState('')

  const mutation = useCheckoutMutation()

  async function onSubmit(e) {
    e.preventDefault()
    if (!holder.trim()) {
      setHolderError('请填写保管人')
      return
    }
    setHolderError('')
    setSubmitError('')
    try {
      await mutation.mutateAsync({ assetId, body: { holder: holder.trim(), location: location.trim() || null, note: note.trim() || null } })
      toast.success('派发成功')
      onOpenChange(false)
      // 清空 state 由 onOpenChange 副作用承担
    } catch (err) {
      setSubmitError(toFriendlyMessage(err))
    }
  }

  // 关闭时清空 state
  useEffect(() => { if (!open) { setHolder(''); setLocation(''); setNote(''); setHolderError(''); setSubmitError('') } }, [open])

  return (
    <Dialog open={open} onOpenChange={(v) => !mutation.isPending && onOpenChange(v)}>
      <DialogContent>
        <DialogHeader><DialogTitle>派发资产</DialogTitle></DialogHeader>
        {submitError && <ErrorBanner>{submitError}</ErrorBanner>}
        <form onSubmit={onSubmit} className="space-y-4">
          <Field label="保管人" required error={holderError}>
            <Input value={holder} onChange={(e) => setHolder(e.target.value)} disabled={mutation.isPending} autoFocus />
          </Field>
          <Field label="位置（可选）">
            <Input value={location} onChange={(e) => setLocation(e.target.value)} disabled={mutation.isPending} />
          </Field>
          <Field label="备注（可选）">
            <Textarea value={note} onChange={(e) => setNote(e.target.value)} disabled={mutation.isPending} rows={3} />
          </Field>
          <DialogFooter>
            <Button type="button" variant="ghost" onClick={() => onOpenChange(false)} disabled={mutation.isPending}>取消</Button>
            <Button type="submit" disabled={mutation.isPending}>
              {mutation.isPending ? '派发中…' : '确认派发'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
```

#### ReturnDialog

结构同上，但：
- 字段只有 `note`（可选）
- 顶部 read-only 上下文区：
  ```tsx
  {currentCheckout
    ? <div className="rounded-md bg-muted px-3 py-2 text-sm">
        当前派发给 · <strong>{currentCheckout.holder}</strong>
        {currentCheckout.location && <> · {currentCheckout.location}</>}
        <br />
        派发于 · <time className="font-code">{formatDate(currentCheckout.checked_out_at)}</time>
      </div>
    : <ErrorBanner>此资产当前无派发中记录，请刷新页面</ErrorBanner>}
  ```
- 若 `currentCheckout === null`：submit 按钮直接 disabled（data race 保护）

#### 失败处理（共用）

所有 mutation 失败：
- Dialog 保持打开
- 顶部渲染 `<ErrorBanner>`（友好文案来自 `toFriendlyMessage`）
- **不弹 Toast**（避免双通道噪声）

### 7.8 NotFoundPanel

新组件，与 EmptyState 视觉同源（避免重复设计）：

```tsx
<div className="flex flex-col items-center justify-center py-24 text-center space-y-4">
  <SearchX className="h-12 w-12 text-muted-foreground" />
  <h2 className="text-xl font-medium">资产不存在</h2>
  <p className="text-muted-foreground max-w-md">它可能已被删除，或链接有误。</p>
  <Link to="/"><Button variant="outline">返回列表</Button></Link>
</div>
```

### 7.9 列表页接通

`features/assets/list/assets-table.tsx` 修改点：
- 表格行 `<tr>` 内嵌一个 transparent overlay `<Link to="/assets/$id">` 元素（绝对定位 inset-0，z-index 低于 ⋯ 按钮），实现：① 中键打开新 tab 的浏览器原生支持；② 不破坏 cell 内 ⋯ 按钮的事件冒泡。`<tr onClick>` 不用——避免与 overlay link 重复触发
- ⋯ 菜单 4 项：派发/归还解 disabled 接 Dialog；编辑/删除维持 disabled 文案"M2c-3 开放"

DropdownMenuItem 派发逻辑（按 `row.status === 'IDLE'` enable）：
```tsx
<DropdownMenuItem
  onSelect={() => setCheckoutDialogState({ open: true, assetId: row.id })}
  disabled={row.status !== 'IDLE'}
>派发</DropdownMenuItem>
<DropdownMenuItem
  onSelect={() => setReturnDialogState({ open: true, assetId: row.id })}
  disabled={row.status !== 'IN_USE'}
>归还</DropdownMenuItem>
```

列表页 Dialog 状态 lift 到 `AssetListPage` 顶层，`AssetsTable` 通过 callback 触发。

## 8. 错误处理（4 层，承接 M2c-1 §8）

| 层 | 触发 | 处理 |
| --- | --- | --- |
| **Router parseParams** | URL 中 `:id` 不是合法 UUID（手输错 / 链接腐烂） | Zod 抛错 → Route `errorComponent: NotFoundPanel` 接收 |
| **Query (asset detail)** | 后端 404 | `useAssetDetailQuery` 的 `onError` 区分：`error.status === 404` → 页面态切 NotFoundPanel；其他 → ErrorState |
| **Query (history / attachments)** | 局部失败 | 区块内 mini ErrorState，不污染全页 |
| **Mutation** | checkout/return/deleteAttachment 失败 | Dialog 内 inline ErrorBanner；不弹 Toast；Dialog 保持打开 |
| **未捕获异常** | 渲染期 throw（e.g. customFieldFormatter 数据脏） | 复用 M2c-1 全局 `<ErrorBoundary>` |

## 9. 不引入 Vitest

继承 M2c-1 §9 决策：M2c-3 引入 Vitest + Testing Library + RHF + Zod 一次到位。

M2c-2 验证全靠：
- `pnpm build` + `pnpm lint` 全绿
- 附录 A 的 12 项手工烟测
- frontend-design skill 合并前 review
- §3.5 红线 grep 扫描

`current-checkout.ts` 和 `custom-field-formatter.ts` 的纯函数属性是为了 M2c-3 引入 Vitest 后**第一批可单测对象**——本里程碑写出来时就刻意保持纯净。

## 10. 扩展兼容性 / M3 候选增强清单

> M3 spec 起草时直接 import 此节。

### 10.1 派出类型扩展（"向外出借"）

**触发场景**：M3 引入"向外出借"作为派发的第二种类型，归还语义不变。

**改动点**：
- 后端：`CheckoutRecord` 模型加 `kind: enum('internal', 'external')` 字段；`CheckoutCreate` DTO 加 `kind`；`CheckoutService.checkout` 接收 kind；DB migration（已有数据回填 `internal`）
- 前端 `checkout-actions.ts`：`CHECKOUT_VERB = '派发'` 升级为：
  ```ts
  export const CHECKOUT_TYPES = [
    { key: 'internal', verb: '派发', dialogTitle: '组内派发', icon: Users },
    { key: 'external', verb: '借出', dialogTitle: '向外出借', icon: ExternalLink },
  ] as const
  ```
- 前端 `AssetHeader` CTA：从单 Button 升级为 split-button（`<Button>派发</Button><DropdownMenu>借出</DropdownMenu>`），布局不变
- 前端 `CheckoutDialog`：表单顶部加 `<RadioGroup>` 选派出类型；submit 时把 kind 一并提交

**M2c-2 当前已留好的兼容**：
- `checkout-actions.ts` 文件已建，CTA 文字从此处导出（不硬编码于组件）
- `CheckoutDialog` 接收 `assetId` 而非依赖 detail page 上下文（列表页 ⋯ 菜单也能复用）
- `useCheckoutMutation` 的 mutationFn 入参用 `body` object 包装（未来扩 `kind` 字段不破坏调用方）

### 10.2 流转 Timeline 视觉重构

**M2c-2 现状**：2 节点形态（当前派发实心 / 历史空心）+ 1 文字标"进行中"

**M3 候选增强**：
1. **时间近远渐隐**：旧记录卡片 opacity 分级（≤90d 100% / ≤180d 80% / 更早 60%），形成"时间向远处淡去"
2. **派出类型染色**（与 §10.1 联动）：组内派发用蓝调点、向外出借用琥珀点；归还后退到 muted；归还后保留类型边框作为线索
3. **超长派发预警**：当前派发节点未归还 > 90 天 → 节点加 `Clock` icon + `text-destructive` 警示色 + 卡片标 "派发 {n} 天"

落地时机：M3 spec 与 §10.1 同周期写。

### 10.3 后端字段补齐

**M2c-1 + M2c-2 共同遗留**，M3 一次性补：
- `Asset.asset_code`（`<type_prefix>-<year>-<序号>`，主识别符；列表页第二列从 SN 切回 asset_code）
- `Asset.type_name` 反规范化或 relationship attribute（去除 M2c-1 客户端 join）
- `Asset.current_checkout_id`（去除 M2c-2 前端 history 推导，详情页可单 endpoint 完整渲染）
- `AssetType.code_prefix`（用于 asset_code 自动生成）

CLI / API / 前端三处协同；DB migration 含历史数据回填规则。

### 10.4 M2c-3 预期对 M2c-2 的迁移

引入 RHF+Zod+Vitest 时一并把 M2c-2 的两个 Dialog 迁到 RHF 版本（约半天工作量），与新建的 `AssetForm` 统一表单栈。

迁移**只动表单状态 + 校验那层**，不动：
- Dialog JSX 骨架 / 文案 / 样式
- Toast / ErrorBanner 逻辑
- mutation hook 接口

M2c-3 plan 起草时，把"迁移 M2c-2 两个 Dialog 到 RHF"明写为一个独立 Task。

## 11. DoD（Definition of Done）

实施期最后一个 Task 必须全部勾选才允许合并：

- [ ] `pnpm --dir frontend build` 全绿
- [ ] `pnpm --dir frontend lint` 全绿
- [ ] `pnpm --dir frontend run gen:openapi` 后无 schema diff（后端 API 形状未漂移）
- [ ] 附录 A 手工烟测 12 项全部通过
- [ ] §3.5 红线扫描（grep `scale-` / `animate-spin` / `backdrop-blur` / `gradient` 在 M2c-2 新增 16 个文件内 0 命中）
- [ ] frontend-design skill 合并前 review 通过
- [ ] 主 doc `2026-04-15-asset-hub-design.md` §2.1 第 3 条括注追加完成（M3 借出类型一句话）
- [ ] `design-system/asset-hub/MASTER.md` 末尾"实施期纠偏（M2c-2）"区块写完（包含 timeline M3 重构清单的提醒）
- [ ] M2c-1 列表页"行点击 + ⋯ 派发/归还"已接通，原 disabled 项 tooltip 文案已更新（编辑/删除 → "M2c-3 开放"）
- [ ] MASTER `Pre-Delivery Checklist` 7 项全勾

## 附录 A：手工烟测清单（12 项）

| # | 步骤 | 期望 |
| --- | --- | --- |
| 1 | 列表页点任意行 | 进入 `/assets/<uuid>`，显示该资产详情 |
| 2 | 直接打开 `/assets/<bad-uuid>`（非合法 UUID） | NotFoundPanel + "返回列表"链接 |
| 3 | 直接打开 `/assets/<合法但不存在的 UUID>` | NotFoundPanel |
| 4 | kill 后端 → 详情页刷新 | ErrorState + Retry；拉起后端点 Retry 成功渲染 |
| 5 | IDLE 资产点 "派发" → 填 holder 提交 | Dialog 关闭 + Toast "派发成功" + Header 切到 IN_USE + 显示 "当前派发给 X" + Timeline 多一条 "进行中" |
| 6 | IN_USE 资产点 "归还" → 提交 | Dialog 关闭 + Toast "归还成功" + Header 切回 IDLE + Timeline 末条 returned_at 填上 |
| 7 | 派发 Dialog 不填 holder 提交 | inline error "请填写保管人"，按钮不进入 pending；mutation 不发起 |
| 8 | 派发 Dialog 提交时手动 mock 后端 500（如 kill 后端）| Dialog 保持打开 + 顶部 inline ErrorBanner，Toast 不弹 |
| 9 | MAINTENANCE / RETIRED 资产页面 | CTA disabled + tooltip 显示原因 |
| 10 | 附件区点缩略图 | Lightbox 打开；图 → 大图居中 contain；非图 → 元信息卡片 + "新窗口打开"按钮 |
| 11 | Lightbox 内点删除 → AlertDialog 确认 → 确认 | Toast "附件已删除" + AlertDialog 关 + Lightbox 关 + 网格刷新少一项 |
| 12 | 切 Light/Dark/System，详情页全部颜色 | 无闪烁、4 态状态色正确、timeline 节点色随主题翻转 |

附加（非烟测，自动化）：Lighthouse a11y ≥ 95（详情页 DOM 比列表页简单，达标无悬念）。

---

**Spec 完毕。** 下一步：spec 自检 → 用户 review → writing-plans skill 生成实施计划。
