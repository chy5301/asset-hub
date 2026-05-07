# M3d · Timeline 视觉重构 + simplify §7 搭车 设计

**日期**：2026-05-07
**关联**：[M3 总览](./2026-05-03-m3-overview-design.md) §3.4 · [M3a 状态机](./2026-05-03-m3a-state-machine-design.md)（KIND_META 现状）
**前置**：M3a (状态机基建) ✅ + M3b (看板) ✅ + M3c (导出) ✅ 已 ship；M3d 串行接续

**brainstorm 决策追踪**：本 spec brainstorm 阶段经 frontend-design skill 二轮独立评审，**推翻了"卡片粒度色条/染色"路径**，最终采用"周期粒度（Group rail）+ 月份粒度（sticky heading）"两层分组结构。详见 §1.2。

---

## 0. 范围

### 包

**A 三件套** timeline 视觉重构（其中 1 件砍掉，2 件实施）：

- ✅ §14.8 派出类型染色 → **E2 形态**：Group rail + 月份分段（§3.1）
- ❌ ~~§14.8 时间渐隐~~ → **本 spec 决议砍掉**（理由 §1.1）
- ✅ §14.8 超长派发预警 → 基于 `due_at`，两阶段（< 7d 黄 / 超期 红），出现在 timeline + AssetHeader（§3.3）

**chip icon 系统统一**（§3.2）：
- 5 替换：CHECKOUT_EXTERNAL（与 INTERNAL 共用 ArrowRightFromLine）/ CheckCircle2 → PackageCheck / Moon → Archive / Sun → ArchiveRestore / UserCog → ArrowLeftRight
- 5 保留：ArrowRightFromLine / Undo2 / Wrench / Trash2 / MapPin

**timeline 卡时间格式**（§3.4）：`2026-04-29 · 5 天前`

**CheckoutDialog 加 due_at 日期 picker（可选字段）**（§3.5）：派发 / 出借共用，不填则不预警

**C 三搭车**（simplify §7，§4）：
- C-1 TypesTable motion 三时刻
- C-2 globals.css type scale 节 + 现有 3 H1 对齐（含 type-detail-page H1 升级；看板 hero H1 不纳入）
- C-3 attachment-grid `transition-shadow` → `transition-all`

**视觉一致性配套**：
- timeline loading skeleton 在月份分组下保持 M3a 现状（裸 ol + 3 卡，**不模拟月份分组**）
- timeline empty/error 态保持现状（M3a 已用 EmptyState / ErrorState）
- a11y：月份分组用 `<div>` 不嵌套 list；`<h3>` 提供屏幕阅读器导航锚点；rail span 全部 `aria-hidden`

### 不包（明确 v2+ 或其他里程碑）

- ❌ 看板视觉（M3b 已交付）
- ❌ 状态机改动（M3a 已交付）
- ❌ §14.4 People 实体化（M5）
- ❌ RELOCATE / TRANSFER_HOLDER 单独 `--status-shift` cyan token（frontend-design 建议但不在 M3d scope，留 M3e/M4）
- ❌ formatRelative 月级/年级 fallback（v1 单台资产 timeline 不会很老，YAGNI；超出仍用 "{n} 天前"）
- ❌ 列表页 overdue 预警（视觉过载，看板 IdleTopBarChart 已承载）
- ❌ overdue 后端字段（保持 schema 不变，纯前端计算）

## 1. 关键决策与理由

### 1.1 时间渐隐砍掉

**决议**：不做 spec §14.8 原文 "≤90d 100% / ≤180d 80% / 更早 60%" 的 opacity 三档渐隐。

**理由**：

1. M3d 已选 E2 形态：Group rail（派出周期分组）+ 月份 sticky heading（时间分段）—— 时间分层信号已经做到两层
2. 月份分段是**中性的"组织"**信号；opacity 渐隐是**带价值判断的"褪色"**——它暗示"老的不重要"，但 v1 业务里"6 个月前的 RETIRE / DISPOSE"恰恰是关键节点
3. 单人项目 v1 单台资产 timeline 一辈子大概 < 30 卡，不存在"屏幕信息过密需要降权"的前提
4. 实施期成本：渐隐要计算每张卡 daysAgo 再分档算 opacity，引入额外纯函数 + 单测；砍掉省一层

**修订 §14.8**：原条款 "时间近远渐隐" 在 M3d 决议**作废**。后续若复活渐隐，需独立重新 brainstorm。

### 1.2 派出类型染色：周期粒度而非卡片粒度

**brainstorm 二轮 frontend-design 评审证伪 "卡片粒度色条 / 染色" 路径**——把 10 个 transition kind 全部展开后，原 C·tuned (3px 色条) / D (chip 容器升级) 都暴露三个真问题：

1. **左缘节奏断裂**：10 张卡里仅 3-4 张带色条，左缘"凸—凸—直—凸—直—直"散点状，看起来像 bug 不像设计
2. **派出周期被中性卡打散**：RELOCATE / TRANSFER_HOLDER 夹在 CHECKOUT 和对应 RETURN 之间，色条想圈"派出 → 归还"区段，被中性卡硬切开
3. **5% tint 在多色相场景下消失**：90d/50d 两条 RETURN 的 5% alpha tint，旁边是满饱和度的紫色退役 chip + 橙色送修 chip + 灰色处置 chip——5% tint 完全淹没

**改用"周期粒度 + 月份粒度"两层分组结构**：

- **Group rail（周期粒度）**：派发卡 → 归还卡之间所有卡（含中性 RELOCATE / TRANSFER_HOLDER）共享 2px 左侧 rail，按派出类型染色（蓝 / 琥珀）—— 把"派出周期"作为时间段视觉收编
- **月份 sticky heading（月份粒度）**：长 timeline 滚动时永远知道在哪个月

详见 §3.1。卡片本身保持 M3a 现状（chip + icon + pill 文字），不重复染色。

### 1.3 chip icon 信号正交分解

**原则**：

- icon 表达**动作家族**（派出 / 归还 / 维修 / 退役 / 处置 / 位置 / 保管人）—— 用形状区分，stroke outline 风格统一
- chip 颜色（status token）表达**动作子类 / 状态归属**—— 用色相区分
- pill 文字表达**精确名称**—— 用文字区分

**关键推论**：CHECKOUT_INTERNAL（派发）和 CHECKOUT_EXTERNAL（出借）是**同一动作家族（派出）**，共用 ArrowRightFromLine icon，由 chip 颜色（蓝 / 琥珀）和 pill 文字（派发 / 出借）分化。

**收敛规则**：

- 全部 lucide outline/stroke 风格（24×24 viewBox / stroke-width 2 / fill none）
- **禁用复合 glyph**（UserCog 类多元素，size-4 下糊成一团）
- **禁用浪漫化抽象隐喻**（自然元素 / 拟人 等与"动作 / 状态"无直接物质对应的隐喻）—— Moon = 退役、Sun = 重启用 是把中文文案望文生义翻成自然意象，落地后 Moon icon 跟"暂停服役"的业务语义无直接物质映射
- **允许语义直接映射隐喻**（动作工具 / 仓储 / 资产生命周期物质对应）—— `Archive`（封箱）↔ `ArchiveRestore`（开箱）= "暂停服役 → 重启用"的物质对应，`Trash2` = "处置"的标准 affordance，`Wrench` / `PackageCheck` = "送修 / 修好"的工具→包裹流程
- **禁用带外圈状态符号**（CheckCircle2 类，与 RETURN/REINSTATE 撞"好结果"语义）
- 同状态簇内有"对偶感"（Wrench ↔ PackageCheck 工具→包裹 / Archive ↔ ArchiveRestore 封箱→开箱 / 派发 ↔ 出借共用 ArrowRightFromLine 由颜色分化）

详见 §3.2 KIND_META 表。

### 1.4 超长派发预警基于 due_at

**决议**：超期判断以每条 OPEN CHECKOUT 的 `due_at` 为基准，纯前端计算。

**理由**：

1. M3a model 已有 `StateTransitionRecord.due_at: datetime | None`（仅 CHECKOUT_* 用）—— 已就位的字段直接消费，**后端零改动**
2. 固定阈值 90d 不合理：笔记本派员工 365d 合理 / 借用品超 14d 才算超期 —— 单一阈值无法覆盖
3. AssetType.checkout_default_days 候选要求 type 加新字段 + 表单 + 列表 UI —— 工作量翻倍，且每种 type 仅一个值，仍不灵活
4. due_at 在派发时由用户填写（dialog 加可选日期 picker），不填等于"我也不知道什么时候归还"是合理状态

**两阶段而非一刀切**：

- `pending`：status === IN_USE && `now < dueAt - 7d` → 无预警
- `due-soon`：status === IN_USE && `dueAt - 7d ≤ now ≤ dueAt` → 黄
- `overdue`：status === IN_USE && `now > dueAt` → 红

详见 §3.3。

### 1.5 列表页不加 overdue 预警

**决议**：列表页保持现状（status chip + 资产名 + 类型 + 保管人 + 时间），不加 overdue 红/黄角标。

**理由**：

1. 列表行已较紧（chip + 多列字段），加预警视觉过载
2. 看板 IdleTopBarChart（M3b）已经有 idle_days > 90 的红色染色 —— 长闲置预警通过看板单独承载
3. 详情页 AssetHeader 角标足以提示"这台资产正在派出且超期" —— 单台资产视图覆盖

## 2. 数据模型 / 计算

### 2.1 后端：零改动

- StateTransitionRecord.due_at 字段 M3a 已落
- 列表 / 详情 / transitions 端点 schema 不变
- ExportService（M3c）不动

### 2.2 前端 utility（新增）

#### `lib/date.ts` 扩展

```ts
export function formatRelative(iso: string, now: Date = new Date()): string {
  // 返回 "今天" / "昨天" / "{n} 天前"
  // v1 仅天级；超出 365d 仍用 "{n} 天前"，未来按需扩月/年
}
```

#### `lib/overdue.ts`（新文件）

```ts
import type { AssetStatus } from "@/features/assets/types";

export type OverdueStatus = "pending" | "due-soon" | "overdue";

export interface OverdueResult {
  status: OverdueStatus;
  days: number;  // 正数 = 还有 N 天 / 还在 pending；负数 days 在 overdue 时取绝对值后传出
}

export function calcOverdue(
  dueAt: string | null,
  assetStatus: AssetStatus,
  now: Date = new Date(),
): OverdueResult | null {
  if (assetStatus !== "IN_USE" || dueAt === null) return null;
  // 实现：differenceInDays(parseISO(dueAt), now) → 分档
}
```

边界处理：恰好 7d / 恰好 0d / 跨自然日（now 14:00 vs dueAt 09:00 同一天）—— 用 `differenceInDays`（date-fns）统一按"日历日"算，避免时区/时分秒漂移。

### 2.3 timeline 派出周期识别

**纯函数 `groupByCheckout(transitions)`**（在 `transition-timeline.tsx` 内或单独 helper）：

输入：按 `created_at` desc 排好的 transitions 数组（API 返回原始顺序）
输出：每条 transition 加 `group: { kind: 'in-use' | 'external' | null, position: 'start' | 'middle' | 'end' | null }`

算法（倒序遍历，最旧→最新）：

- 遇 CHECKOUT_INTERNAL/EXTERNAL：开新派出周期，标记 `position='start'`，记下 group kind
- 周期内的 RELOCATE / TRANSFER_HOLDER：标记 `position='middle'` + 继承 kind
- 遇 RETURN：闭合周期，标记 `position='end'`
- 周期外 transition（送修 / 退役 / 处置等）：group=null
- **OPEN CHECKOUT**（status === IN_USE 且无对应 RETURN）：周期"向更新方向"延续到 status 离开 IN_USE 为止；如果到列表头还没离开 IN_USE，所有"上方"中性卡都属于此周期

**防御**：状态机 INVARIANT 保证序列合法（M3a），实际不会出现"RETURN 没有对应 CHECKOUT"；防御性返 group=null。

### 2.4 月份分组

纯函数 `groupByMonth(transitions)` → `[{ month: '2026-05', items: [...] }, ...]`，月份按 created_at 切（`format(parseISO(iso), 'yyyy-MM')`），desc 排序。

## 3. 视觉规范

### 3.1 Group rail + 月份分段（E2 形态）

#### Group rail

**关键约束**：`<ol>` 用 `space-y-3`（卡间 12px gap），rail 必须**跨过 gap**才视觉连续。做法：rail span 用 `absolute`，**non-end 卡的 rail 向下延伸 -12px 跨过 gap 到下张卡顶**；end 卡的 rail 在 li 内底部封口。**li 不加 `overflow-hidden`**（默认 visible，否则 rail 跨 gap 会被裁）。

```tsx
<li className="rounded-lg ring-1 ring-border/60 p-3 flex items-start gap-3 relative">
  {group?.kind && group.position !== "end" && (
    <span
      className={cn(
        "absolute left-0 w-0.5",                            // 2px
        "-bottom-3",                                         // 跨过 12px gap 到下张卡
        group.position === "start" ? "top-1.5" : "top-0",   // start 顶部留 6px 封口
        group.kind === "in-use" && "bg-status-in-use/40",
        group.kind === "external" && "bg-status-borrowed/40",
      )}
      aria-hidden
    />
  )}
  {group?.kind && group.position === "end" && (
    <span
      className={cn(
        "absolute left-0 w-0.5 top-0 bottom-1.5",            // end 卡内收束，底部留 6px 封口
        group.kind === "in-use" && "bg-status-in-use/40",
        group.kind === "external" && "bg-status-borrowed/40",
      )}
      aria-hidden
    />
  )}
  {/* 现有 chip + body + time */}
</li>
```

**形态约束**：

- 宽度：`w-0.5`（2px），与 `ring-1 ring-border/60` 量级协调
- 颜色：
  - INTERNAL 周期：`bg-status-in-use/40`
  - EXTERNAL 周期：`bg-status-borrowed/40`（新 token，§3.6）
- **rail 连续性靠 `-bottom-3` 跨过 `space-y-3` gap** —— 多张连续卡 rail 视觉无缝
- start 卡（CHECKOUT）：`top-1.5` 顶部留 6px 封口
- middle 卡（派出期内的 RELOCATE / TRANSFER_HOLDER）：`top-0` 满高
- end 卡（RETURN）：`top-0 bottom-1.5` 底部 6px 封口（不 -bottom-3，rail 在 li 内收束）

#### 月份 sticky heading

```tsx
<h3 className="sticky top-0 bg-background pb-1.5 pt-3 text-xs uppercase tracking-wide text-muted-foreground border-b border-border/40 font-medium first:pt-0 z-10">
  {month}
</h3>
```

**约束**：

- **不用 `backdrop-blur`**（M2c-2 红线）。背景用 `bg-background`（不透明）保证 sticky 时下方 timeline 内容不穿透
- `z-10` 保 sticky 时 heading 浮于卡上方
- `first:pt-0` 首个月份不留多余 padding（贴 section 顶）

#### Render 结构

**决议**：不用 ol > li > h3 + ol 嵌套（li 包 h3 语义糊）。改 `<section>` + 月份分组用 `<div>` 平铺 + 卡片仍用 `<ol>` 保 list 语义：

```tsx
<section>
  <h2 className="mb-3 text-lg font-medium">流转记录</h2>
  {query.isLoading ? (
    <TimelineSkeleton />
  ) : query.isError ? (
    <ErrorState ... />
  ) : (data ?? []).length === 0 ? (
    <EmptyState ... />
  ) : (
    months.map(({ month, items }) => (
      <div key={month} className="mb-3">
        <h3 className="sticky top-0 bg-background pb-1.5 pt-3 text-xs uppercase tracking-wide text-muted-foreground border-b border-border/40 font-medium first:pt-0 z-10">
          {month}
        </h3>
        <ol className="space-y-3 mt-2">
          {items.map(t => <TransitionCard key={t.id} transition={t} group={t.group} />)}
        </ol>
      </div>
    ))
  )}
</section>
```

**loading 态**：保持 M3a 现有 `TimelineSkeleton` 形态（裸 ol + 3 张骨架卡，**不模拟月份分组**）—— loading 状态显示假月份会让用户产生"已经知道有几个月"的错觉，反而更糟。

**a11y**：每个月份分组用 `<div>` 不用 list 嵌套；`<ol>` 在每个月份内独立保 list 语义；`<h3>` 自带 heading level 让屏幕阅读器导航能跳到月份。

### 3.2 chip icon 系统

#### KIND_META 改写（5 替换 + 5 保留）

```ts
import {
  ArrowRightFromLine, Undo2,
  Wrench, PackageCheck,
  Archive, ArchiveRestore,
  Trash2, MapPin, ArrowLeftRight,
  type LucideIcon,
} from "lucide-react";

const KIND_META: Record<TransitionKind, KindMeta> = {
  CHECKOUT_INTERNAL:        { label: "派发",       Icon: ArrowRightFromLine, bgClass: "bg-status-in-use/15",      fgClass: "text-status-in-use-fg" },
  CHECKOUT_EXTERNAL:        { label: "出借",       Icon: ArrowRightFromLine, bgClass: "bg-status-borrowed/15",    fgClass: "text-status-borrowed-fg" },  // ← icon 共用、颜色分化
  RETURN:                   { label: "归还",       Icon: Undo2,              bgClass: "bg-status-idle/15",        fgClass: "text-status-idle-fg" },
  SEND_TO_MAINTENANCE:      { label: "送修",       Icon: Wrench,             bgClass: "bg-status-maintenance/15", fgClass: "text-status-maintenance-fg" },
  RECOVER_FROM_MAINTENANCE: { label: "维修完成",   Icon: PackageCheck,       bgClass: "bg-status-idle/15",        fgClass: "text-status-idle-fg" },       // ← 替 CheckCircle2
  RETIRE:                   { label: "退役",       Icon: Archive,            bgClass: "bg-status-retired/15",     fgClass: "text-status-retired-fg" },     // ← 替 Moon
  REINSTATE:                { label: "重新启用",   Icon: ArchiveRestore,     bgClass: "bg-status-idle/15",        fgClass: "text-status-idle-fg" },        // ← 替 Sun，与 Archive 视觉成对
  DISPOSE:                  { label: "处置",       Icon: Trash2,             bgClass: "bg-status-disposed/15",    fgClass: "text-status-disposed-fg" },
  RELOCATE:                 { label: "变更位置",   Icon: MapPin,             bgClass: "bg-muted",                 fgClass: "text-muted-foreground" },
  TRANSFER_HOLDER:          { label: "变更保管人", Icon: ArrowLeftRight,     bgClass: "bg-muted",                 fgClass: "text-muted-foreground" },     // ← 替 UserCog
};
```

`Send` / `CheckCircle2` / `Moon` / `Sun` / `UserCog` 五个 icon import 在 PR 中**移除**（不留死引用）。

### 3.3 超长派发预警

#### 视觉位置 1 · timeline OPEN CHECKOUT 卡

CHECKOUT_INTERNAL / CHECKOUT_EXTERNAL 在 `assetStatus === 'IN_USE'` 且 `due_at` 非空时，卡内文案下方追加 overdue 提示行。**`font-medium` 是关键**——避免视觉重量被 `t.note`（`text-xs text-muted-foreground`）压制：

```tsx
{overdue && overdue.status !== "pending" && (
  <p className={cn(
    "text-xs font-medium mt-1 inline-flex items-center gap-1",
    overdue.status === "due-soon" && "text-warning-fg",
    overdue.status === "overdue" && "text-destructive",
  )}>
    <Clock className="size-3" aria-hidden />
    {overdue.status === "due-soon" && `还有 ${overdue.days} 天到期`}
    {overdue.status === "overdue" && `逾期 ${overdue.days} 天`}
  </p>
)}
```

#### 视觉位置 2 · AssetHeader 角标

`asset-header.tsx` 顶部资产名旁加角标（仅 OPEN CHECKOUT 状态：`assetStatus === 'IN_USE'` 且能找到 OPEN CHECKOUT transition 的 `due_at`）：

```tsx
{overdue && overdue.status !== "pending" && (
  <span className={cn(
    "ml-3 inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium",
    overdue.status === "due-soon" && "bg-warning/15 text-warning-fg",
    overdue.status === "overdue" && "bg-destructive/15 text-destructive",
  )}>
    <Clock className="size-3" aria-hidden />
    {overdue.status === "due-soon" && `还有 ${overdue.days} 天到期`}
    {overdue.status === "overdue" && `逾期 ${overdue.days} 天`}
  </span>
)}
```

颜色 token 与现有 status pill 体系（status-badge.tsx）一致采用**双 token**模式：`bg-{color}/15 text-{color}-fg`。新建 `--warning` + `--warning-fg` 双 token（§3.7）。

`overdue` 计算流程：

1. `useTransitionsQuery(assetId)` 拿 transitions 列表 —— **同 hook 复用零成本**：M3a 的 `transition-timeline.tsx` 已在 detail page 内调 `useTransitionsQuery(assetId)`，AssetHeader 调同 hook 同 assetId 时 React Query 自动 dedupe（同 queryKey），不会发出第二次网络请求
2. 找 **OPEN CHECKOUT** —— 同时满足：(a) `kind === 'CHECKOUT_INTERNAL' || kind === 'CHECKOUT_EXTERNAL'`，(b) 不存在任何 RETURN transition 的 `closes_transition_id` 引用它
3. 取该 OPEN CHECKOUT 的 `due_at` + 当前 `asset.status`，调 `calcOverdue(dueAt, status)` 返 `OverdueResult | null`

### 3.4 timeline 卡时间格式

```tsx
<time className="text-xs text-muted-foreground font-code shrink-0">
  {formatDate(t.created_at)} · {formatRelative(t.created_at)}
</time>
```

中点分隔符 `·` 与列表/详情已有惯例一致（`holder · location` 等）。

### 3.5 CheckoutDialog 加 due_at picker

`checkout-dialog.tsx`（CHECKOUT_INTERNAL / CHECKOUT_EXTERNAL 共用此 dialog）表单加日期 picker。**不引入新依赖**：项目已装 `react-day-picker@^9.14.0`，`frontend/src/components/ui/calendar.tsx` + `popover.tsx` 已就位，且 `features/assets/form/field-controls/date-field.tsx`（`acquired_at` 字段已用）是现成范本，直接复用 Popover + Calendar 模式：

```tsx
import { CalendarIcon } from "lucide-react";
import { format } from "date-fns";
import { zhCN } from "date-fns/locale";
import { Button } from "@/components/ui/button";
import { Calendar } from "@/components/ui/calendar";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";

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
            onSelect={(d) => field.onChange(d ? format(d, "yyyy-MM-dd") : undefined)}
            disabled={(d) => d < new Date(new Date().setHours(0,0,0,0))}  // 不允许选过去
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

**注意**：

- 表单内部存 `'yyyy-MM-dd'` 字符串（与 `acquired_at` 一致）；提交前再转 ISO datetime（`{date}T00:00:00` 当地时区）随 transition body 发后端
- `due_at` 字段在 `useCreateTransition`（或 transitions API client）请求 body 中已就位（M3a 后端 schema 已含），前端零后端契约改动
- 不直接抽 `DateField` 复用：CheckoutDialog 用 RHF + zod 资产 schema，与 asset-form 的 fieldDef 驱动结构异构；按 dialog 现有 FormField 模式直写更轻

### 3.6 新建 `--status-borrowed` token

`design-system/asset-hub/MASTER.md` "Status token 体系"节加：

```
| --status-borrowed     | 琥珀（amber），hue ≈ 75° | CHECKOUT_EXTERNAL（对外出借）chip / Group rail external |
| --status-borrowed-fg  | 同色相深 fg              | 同上 chip 文字色 |
```

**色相距离约束**：

- 与 `--status-maintenance`（橙，hue ≈ 30°）拉开 ≥ 45° —— 满足
- 与 `--chart-2`（橙，hue ≈ 30°）拉开 ≥ 45° —— 满足
- 与 `--chart-4`（黄，hue ≈ 80°）距离 5° —— 接受：chart token 是看板派色槽，与 timeline status token 不在同一视图共现

**OKLCH 参考值**（具体数值实施期调，保持 light/dark 对比度 AA）：

```css
/* light */
--status-borrowed: oklch(0.78 0.13 75);
--status-borrowed-fg: oklch(0.42 0.13 75);

/* dark */
--status-borrowed: oklch(0.70 0.13 75);
--status-borrowed-fg: oklch(0.85 0.10 75);
```

dark mode 调亮 lightness 保对比度（参考已有 status token 双主题约定）。

### 3.7 新建 `--warning` + `--warning-fg` token

项目当前无 `--warning` 通用语义 token（status-* / destructive 已覆盖大部分场景，但 due-soon 黄色警示无现成 token）。本 PR 引入双 token：

```css
/* light */
--warning: oklch(0.85 0.18 90);     /* amber 黄 */
--warning-fg: oklch(0.45 0.15 90);

/* dark */
--warning: oklch(0.72 0.18 90);
--warning-fg: oklch(0.88 0.13 90);
```

**色相距离约束**：与 `--status-borrowed`（hue ≈ 75°）拉开 15°——临界但接受：两者语义关联（"出借"+"快到期"经常同卡出现），同色系反而强化"派出场景的警示"叙事；用 lightness/chroma 区分明暗即可（warning 更亮、border 更亮）。

`globals.css` 同步 light + dark 双主题；MASTER.md "Status token 体系"节文档化。

## 4. C 三搭车（simplify §7）

### C-1 · TypesTable motion 三时刻

**位置**：`frontend/src/features/types/list/types-table.tsx`

复制 `assets-table.tsx` 的模式：

```tsx
const bodyKey = query.dataUpdatedAt;  // React Query 提供
return (
  <table>
    <thead>...</thead>
    <tbody key={bodyKey} className="tbody-fade">
      {rows.map((row, i) => (
        <tr
          key={row.id}
          className="stagger-row"
          style={{ animationDelay: `${i * 30}ms` }}
        >
          {/* cells */}
        </tr>
      ))}
    </tbody>
  </table>
);
```

`tbody-fade` / `stagger-row` 已在 `globals.css` 定义（M2 视觉收尾），不引入新 CSS。

### C-2 · 页面 H1 type scale

**约定**（写入 `globals.css` 顶部注释 + MASTER.md "排版" 节）：

| 页面分类 | H1 utility | 用例 |
|---|---|---|
| 列表 / 配置页 | `text-xl font-semibold` | `/types`（类型列表）/ `/assets`（列表页 H1 由 SectionHeading 承担，这里指页面标题级别） |
| 详情页 | `text-2xl font-semibold` | `/assets/:id` / `/types/:id` |
| **看板（hero）** | 不纳入此约定 | `/dashboard`（M3b 已交付 `text-3xl font-medium tracking-tight`）—— hero 页有副标 + radial atmosphere，是独立形态 |

**改动现有 3 处**：

| 文件 | 现状 | 改 |
|---|---|---|
| `frontend/src/features/assets/detail/asset-header.tsx`（详情页 H1） | `text-2xl font-semibold` | 保持（已对齐） |
| `frontend/src/features/types/list/types-page.tsx` | `text-xl font-semibold` | 保持（已对齐） |
| `frontend/src/features/types/detail/type-detail-page.tsx` | `text-xl font-semibold` | **改 `text-2xl font-semibold`**（详情页分类） |

实施期 grep 全前端 `text-xl font-semibold` / `text-2xl font-semibold` 确认无第 4 档漏网（如有发现需在本 PR 一并对齐或写入"已知偏离"清单）。

### C-3 · attachment-grid prop 名

**位置**：`frontend/src/features/assets/detail/attachment-grid.tsx:54`

```tsx
- className="... transition-shadow hover:ring-2 hover:ring-primary/40"
+ className="... transition-all hover:ring-2 hover:ring-primary/40"
```

注释或 commit message 说明 `transition-shadow` 监听 `box-shadow`，但 hover 用的是 `ring-*`（底层 box-shadow 实现），所以"凑巧能用"但语义错；改 `transition-all` 让 transition 触发更精准。

## 5. 实施分层

**单 PR 实施**（建议）：M3d 范围相对集中（前端为主，后端零改动），单 PR 包揽。**PR 内分 5 phase commit**：

| Phase | 内容 | 文件 |
|---|---|---|
| 1 · token | `--status-borrowed` + `--warning`（如缺）+ MASTER.md / globals.css 双主题写入 | `design-system/asset-hub/MASTER.md` / `frontend/src/index.css`（plan 阶段 grep 实际路径） |
| 2 · utility | `lib/date.ts` 加 `formatRelative` / `lib/overdue.ts` 新文件 + 单测 | `lib/date.ts` / `lib/overdue.ts` / `tests/unit/format-relative.test.ts` / `tests/unit/calc-overdue.test.ts` |
| 3 · timeline 重构 | KIND_META 替换 + Group rail 算法 + 月份分组 + 时间格式 + render | `transition-timeline.tsx` / `tests/unit/group-by-checkout.test.ts` / `tests/unit/group-by-month.test.ts` / `tests/components/transition-timeline.test.tsx` |
| 4 · 超期预警 | CheckoutDialog 加 due_at picker + AssetHeader 角标 | `checkout-dialog.tsx` / `asset-header.tsx` / 对应 component test |
| 5 · C 搭车 | C-1 motion / C-2 H1 / C-3 attachment | `types-table.tsx` / `type-detail-page.tsx` / `attachment-grid.tsx` |

每 phase 间跑 `pnpm --dir frontend tsc -b` + `pnpm --dir frontend test` + `pnpm --dir frontend lint`；后端零改动也跑一次 `uv run ruff check . && uv run pytest` 兜底确认 import 无漂移。

**Phase 3 末尾视觉 gate**（critical）：timeline 重构是 M3d 视觉重头戏，Phase 3 commit 后**必须**用 playwright MCP 烟测 timeline 视觉再进 Phase 4，避免 Phase 4 角标遮蔽 Phase 3 的潜在视觉问题（rail 跨 gap / sticky h3 / 月份分组 / 新 icon）。Phase 3 视觉验收点见下方烟测清单 step 3。

**PR 规模预估**：~15-20 文件、+800 -200 行。

**playwright MCP 烟测**（实施期手动）：

1. 新建一台资产 → 派发（带 due_at）→ 看 timeline + AssetHeader 显示 due-soon 预警
2. 时间穿越：把测试 db 里 due_at 改到 8 天前 → 刷新看 overdue 红角标
3. 多 transition 历史：手工触发 10 个 transition → 看 Group rail + 月份分段视觉
4. 类型管理页：观察 motion stagger 入场
5. dark mode 切换：所有新色（`--status-borrowed` / `--warning`）双主题 OK
6. 页面 H1 visual 对齐（types-page / type-detail-page / asset-detail-page 三页 H1 字号一致性）

## 6. 测试

### 6.1 Vitest unit（`frontend/tests/unit/`）

| 文件 | 覆盖 |
|---|---|
| `format-relative.test.ts` | 今天 / 昨天 / N 天前 / 跨年（仍用天） |
| `calc-overdue.test.ts` | status !== IN_USE 返 null / dueAt null 返 null / now < dueAt-7d → pending / 边界 dueAt-7d → due-soon / 边界 dueAt → due-soon / now > dueAt → overdue / days 数值正确 |
| `group-by-checkout.test.ts` | 单对 INTERNAL CHECKOUT+RETURN / 单对 EXTERNAL CHECKOUT+RETURN / 中间夹 RELOCATE/TRANSFER_HOLDER 标 middle / OPEN CHECKOUT（无 RETURN）group 延伸 / 周期外 transition group=null |
| `group-by-month.test.ts` | 跨月分组 / 月份 desc 排序 / 同月多条按时间 desc |

### 6.2 Vitest component（`frontend/tests/components/`）

| 文件 | 覆盖 |
|---|---|
| `transition-timeline.test.tsx`（扩展） | 10 kind 各 1 条 → DOM 含正确 icon test-id / pill 文字 / **跨 2 个月数据 → 渲染 2 个 sticky h3 + 月份文案正确** / Group rail 卡归属 / OPEN CHECKOUT overdue → 含 "逾期 N 天" 红文案 |
| `tokens.test.ts`（新） | `getComputedStyle` 验证 `--status-borrowed` / `--warning` / `--warning-fg` 在 light/dark 主题下都有非空值且对比度满足 AA（用 `theme-provider` mock 切主题） |
| `checkout-dialog.test.tsx`（扩展） | 提交 due_at 字段 → request body 含 ISO string / 不填 → body 无 due_at（或 null） |
| `asset-header.test.tsx`（扩展） | status IN_USE + dueAt 8 天前 + transitions 含 OPEN CHECKOUT → render "逾期 8 天" 红角标 / status IDLE + dueAt 任意 → 不 render 角标 / status IN_USE + dueAt null → 不 render |

### 6.3 不写

- e2e（M3e 统一交付 playwright e2e 烟测脚本）
- 视觉 regression 自动化（playwright MCP 手动烟测代替）

## 7. 风险

| # | 风险 | 等级 | 缓解 |
|---|---|---|---|
| R1 | `--status-borrowed`（琥珀 hue 60°）与 `--status-maintenance`（橙 hue 30°）色相相邻，timeline 同时出现送修+出借时难以一眼区分 | 中 | OKLCH hue 严格拉开 ≥ 30°；MASTER.md 写死约束；dark mode 双主题手动校验；如校验后仍不达标，退化方案：`--status-borrowed` 改用更偏黄的 hue（90° 黄绿系）—— plan 阶段决定 |
| R2 | `--warning` token 之前不存在，due-soon 落色无 token 引用 | 低 | 实施期 grep 确认；缺则同 PR 加（amber 系，与 `--status-borrowed` 拉开 ≥ 20°） |
| R3 | `groupByCheckout` 算法对状态机异常序列（数据库手动改坏）行为未定义 | 低 | 防御性返 group=null；不做异常恢复 |
| R4 | sticky 月份 heading 在 detail page 滚动容器层级不对（不在最外层 sticky 失效） | 中 | 实施期 playwright MCP 验证 sticky 在实际 DOM 树中生效；若不生效退化为 inline heading（不影响其他逻辑） |
| ~~R5~~ | ~~项目无 DatePicker~~ | — | **spec 已查证：项目装 react-day-picker 9.14 + Calendar/Popover ui 组件 + DateField 范本 + acquired_at 已用同模式。R5 不存在。整行作废** |
| R6 | `type-detail-page` H1 从 `text-xl` 升到 `text-2xl` 视觉破坏 | 低 | C-2 要求统一详情页 H1；playwright MCP visual 校验 |
| R7 | M3d 视觉重构破坏 M3a 落地的 timeline 已有视觉一致性（用户已习惯当前样子） | 低 | 单仓库内可控，无外部消费者；M3d PR 合并后视觉切换为新形态 |
| ~~R8~~ | ~~AssetHeader 角标依赖 useTransitionsQuery~~ | — | **spec 已查证：transition-timeline.tsx 已调 useTransitionsQuery，AssetHeader 调同 hook 同 assetId 时 React Query queryKey dedupe 零额外网络请求。R8 不存在。整行作废** |
| R9 | 月份 sticky heading 滚动时与 Group rail 视觉打架（rail 顶到 h3 后是否被遮挡 / 视觉是否打断派出周期感）| 中 | h3 用 `bg-background z-10` 不透明 + rail 在 li 内绘制 —— sticky h3 浮起时 rail 视觉被 h3 遮住底部部分，是 **预期行为**（rail 表"派出周期"的视觉收编，h3 表"日历组织"，两者在 z 轴层级上 h3 覆盖 rail 是正确的层级关系，跟实际"派出周期跨多月"的物理现实一致）；playwright MCP 滚动烟测验证视觉合理性 |

### 不缓解的已知风险

- **未来新增 transition kind**（M5 People 实体化 / 借用类型扩展）会同时改 KIND_META + groupByCheckout —— 接受
- **timeline 某条 transition 跨月时 Group rail 被月份 heading 视觉打断** —— 接受（rail 在卡片内绘制，heading 在卡之间，视觉上是"派出周期穿越多月"的天然表达，不是 bug）

## 8. 后续工作

- 本 spec 完结后写实施 plan：`docs/superpowers/plans/2026-05-07-m3d-timeline-visual.md`
- M3d 落地后：
  - `simplify-followups.md` §7 三项标 ✅ 闭环
  - `followup-allocation.md` 摘要表 M3d 标 ✅ 已完成
  - 主 spec §14.8 时间渐隐条款标"M3d 决议作废"
- M3d 落地后**跑一次 Lighthouse a11y 全站扫描**（M2c-1 跑过基线，M3a/b/c/d 大量新视觉后窗口收紧，v1.0 GA 前必须扫一次回归）；扫描 score < 95 的页面在 M3e 修复
- M3e 启动前考虑追加 `--status-shift` cyan token（RELOCATE / TRANSFER_HOLDER 染色升级）
