# 前端视觉/结构一致性 batch — Scope 设计文档

> 日期：2026-05-26
> 类型：scope + 结构决策（视觉决策延后到 frontend-design pass）
> 状态：scope 已锁定，待 frontend-design 决策

## 背景

放弃 M5 + 宣布 v2 功能完整后（见 `2026-05-25-drop-m5-v2-feature-complete.md`），评估"维护态待办里的可选项是否值得打包做"。价值分诊结论：代码整洁类多为 trigger-gated（休眠合理），真正值得做的是**用户最在意的视觉一致性**。随后实机巡检 GUI，浮现一批跨页面的视觉/结构不一致——本 batch 即收口这批问题。

**本 batch 性质**：前端视觉/结构一致性收尾，非新功能。规模够一个小里程碑。

## Scope（已锁定）

6 项，下表为问题 + 已定结构方向。**视觉处理的具体决策延后到 frontend-design pass**（见 §待决策）。

### 1. §W-详情 · 类型详情对齐资产架构（结构重构，最大项）

**现状对比**（资产详情 = 用户满意的基准）：

| 维度 | 资产详情 `/assets/$id` | 类型详情 `/types/$id` |
|---|---|---|
| 页面外壳 | 自带 `<main mx-auto max-w-[960px] px-4 py-8>` 居中窄栏 | 路由层 `<div max-w-3xl>`（768，**无 mx-auto→靠左**，无 padding） |
| 返回按钮 | ✓ `← 返回列表`（`asset-header.tsx`） | ✗ 无 |
| 详情/编辑 | ✓ 详情只读 + 独立 `/assets/$id/edit`（header "编辑"按钮跳转） | ✗ 合并——标题写"编辑类型 - X"，内嵌 `TypeForm mode=edit`，看即编辑（**从无只读视图**） |
| 删除入口 | 收在 ⋯ 下拉（含"需先归还"约束态） | header 右上裸露红按钮 |
| 元信息 | `general-fields.tsx` 定制 dl 行 | `type-summary-card.tsx` grid-cols-2 dl |

**决策（用户已定：完全对齐资产）**：

- 抽共享骨架组件 **`<DetailPageShell>`**：居中窄栏（采用资产的 960 宽）+ 返回链接（slot）+ header（标题左 / actions 右）+ `space-y` 节奏 + children 区。
- 资产详情改用 `DetailPageShell`（基准方，改动小，主要是把现有 header 结构搬进壳）。
- 类型详情**拆两页**，mirror 资产：
  - `/types/$id` → **新建只读视图**（当前不存在）：返回按钮 + 标题=类型名 + 右侧"编辑/删除" + 正文展示元信息 + custom_fields schema（只读）。
  - `/types/$id/edit` → **新建编辑页**：搬 `TypeForm mode=edit`，对应 `assets.$id.edit`。
- 顺带修：删 "编辑类型 -" 标题措辞、裸删除按钮收进一致位置、`max-w-3xl` 靠左 → 居中、补返回按钮。

**涉及文件**：新增 `detail-page-shell`（共享，位置待定，可能 `components/layout/` 或 `features/.../detail`）；`asset-detail-page.tsx` / `asset-header.tsx` 重构；`type-detail-page.tsx` 拆为只读视图 + 编辑页；新增 `routes/types.$id.edit.tsx`，改 `routes/types.$id.tsx`；`type-summary-card.tsx` 可能并入只读视图。

### 2. §W-列表 · 三页 page-header 规范统一（视觉决策）

**现状**：三个顶层页面三套标题处理，无统一规范：

| 页面 | 标题 | 副标题 | 字号 |
|---|---|---|---|
| `/` 资产列表 | **无** | 无（数量在分页页脚） | — |
| `/types` 类型列表 | `类型管理` | `共 N 个类型`（数量） | `text-xl` |
| `/dashboard` 看板 | `看板` | `实时盘点 + 闲置督促`（tagline） | `text-3xl` |

类型列表那个"共 N 个类型"副标题是**漂移**产物（类型无分页页脚，数量只能塞标题下），非系统设计。

**决策方向**：定**一套 page-header 处理规范**（标题字号 / 数量放哪 / 副标题用法），三页统一（或有意识决定哪些页有头）。**具体规范 = frontend-design 决策**。

**合理差异（不动）**：资产列表有 filter/列控制/导出/分页，类型列表都没有——但**类型是小固定集**，不需要这些，功能不对称正当，**不为统一而强加**。

**涉及文件**：`features/assets/list/`（`index.tsx` 顶栏）、`features/types/list/types-page.tsx`、`features/dashboard/dashboard-header.tsx`；可能抽一个轻量 page-header 组件。

### 3. §S · toggle 统一到看板 TogglePill（视觉，小）

**现状**：看板 `dashboard-header.tsx::TogglePill`（圆点前缀 + status token，形态精致）是好的基准；资产列表 filter 的 toggle 是"按下态弱"的那个，两者不一致。

**决策方向**：资产列表 filter toggle 复用/对齐 `TogglePill` 形态。**确认 TogglePill 为基准 = frontend-design 轻决策**。

**涉及文件**：`features/assets/list/assets-filters.tsx`；`TogglePill` 可能从 `dashboard-header.tsx` 提到共享位置。

### 4. D1 · 看板背景渐变 vs 全站平色（视觉决策）

**现状**：`dashboard-page.tsx:36` 给看板整页套 radial 渐变（M4 atmosphere）：中心 `oklch(0.985)` 淡灰 → 边缘纯白；其余页面/header 是平色。交界处有 seam，整体读作"不一致"。M4 #13 修的是 card vs body，没动 radial vs chrome 这层。

**决策方向**：让看板背景与全站统一（去渐变 or 给出全站一致的处理）。**方案 = frontend-design 决策**（含是否保留 atmosphere 概念）。

**涉及文件**：`dashboard-page.tsx`、`globals.css`（`--dashboard-bg-radial-*` token）。

### 5. D2 · 看板右列布局间距过大（布局决策）

**根因**：`dashboard-page.tsx:51,61` 右列 `grid grid-rows-3 ... min-h-[640px]`——为对齐左侧高图强制 3 等高行（~213px）；但行内卡片（`<section>`）无 `h-full`，浮在行顶，下方留死空间 = 大间距；且第 3 卡片 `HolderLeaderboard` 当前无持有人数据（多 IDLE），底部更空。

**决策方向**：改为卡片按内容高度排布、合理处理空持有人卡片（空态或条件渲染）、重新考虑左右等高约束。**布局方案 = frontend-design 决策**。

**涉及文件**：`dashboard-page.tsx`、`features/dashboard/charts/*`、`holder-leaderboard.tsx`（空态）。

### 6. （可选）逾期角标加载闪动（小技术修，非视觉决策）

`asset-header.tsx::useOverdueForOpenCheckout` 在 transitions 加载期返回 null → 角标"先无后突现"轻微跳动。可加 loading 兜底或延迟渲染。**可选，不阻塞本 batch。**

## 待 frontend-design 决策清单

进入 frontend-design pass 时逐条定，结果回写本 spec：

1. **page-header 规范**（§W-列表）：标题字号档位、数量是否/何处展示、副标题用法、三页是否都有头。← 核心视觉决策
2. **只读类型视图布局**（§W-详情）：展示哪些字段、custom_fields schema 只读怎么呈现（列表？卡片？）、与资产 `general-fields` 风格对齐到什么程度。
3. **`DetailPageShell` 视觉细节**：返回链接样式、header 间距、actions 区排布。
4. **看板背景处理**（D1）：去渐变 / 统一 atmosphere / 其它。
5. **看板右列布局**（D2）：卡片高度策略、空持有人卡片处理、等高约束取舍。
6. **toggle 基准确认**（§S）：TogglePill 为准 + 提取位置。

frontend-design 须遵循 `design-system/asset-hub/MASTER.md` + 反 AI-slop 红线（`grep -rnE 'scale-|animate-spin|backdrop-blur|bg-gradient-to'` 期望 0 命中，shadcn `animate-pulse` 历史例外），复用既有公共组件（`<EmptyState>` / `<ErrorState>` / skeleton 等）与 token。

## 明确不做（YAGNI 边界）

- **代码整洁类**（前端 cast 链路 §J/§M/§N/§O、后端 3 minor、§T 结构化 payload）：维护态下休眠，见 M5 决策文档维护态待办快照。本 batch 是**视觉/结构一致性**，不夹带代码重构（除非 §W-详情重构路径上自然触及，则就近处理）。
- **给类型列表加 filter/导出/分页**：类型是小固定集，功能不对称正当。
- **完整跨页面观感重设计**：本 batch 限定在上述 6 项；其它视觉问题"以后发现再说"（用户决定）。

## 流程

scope spec（本文）→ `/frontend-design` 做 §待决策 的视觉决策并回写 → `/writing-plans` 出实现计划。预计实现拆 2 个 PR：

- **PR-1**：`DetailPageShell` 抽取 + 资产详情改用 + 类型详情拆只读视图/编辑页（§W-详情）
- **PR-2**：看板修复（D1/D2）+ page-header 规范统一（§W-列表）+ toggle 统一（§S）+ 可选角标闪动（E）

> 流程说明：brainstorming 通常直接转 writing-plans，但本 batch 视觉主导，按 `CLAUDE.md`（前端视觉决策必须走 frontend-design）中间先过 frontend-design pass。
