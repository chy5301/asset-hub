# M2 视觉收尾设计文档

- **日期**：2026-05-03
- **状态**：待实施
- **作者**：conghaoyangbobby@gmail.com（与 Claude 协同 brainstorm）
- **起点**：2026-05-03 在 brainstorm 会话内 frontend-design skill 对 M2a→M2c-4 全栈做了一次设计契约对照（不落盘为独立报告，决议直接进本 spec），发现 9 项偏差（H1-5 + M1-4）。本里程碑闭环 H 类全部 + 1 项设计抽象（M2 SectionHeading），其余记入 `simplify-followups.md` §7 留给 M3。

---

## 1 范围

**关键词**：M2 阶段（M2a / M2b / M2c-1 / M2c-2 / M2c-3 / M2c-4 / M2d）合并落地后，对照 ui-ux-pro-max MASTER + spec §3.5 设计契约的事后纠偏 PR。

**包括**：

| 项 | 主题 | 类型 |
|---|---|---|
| H1 | `--font-heading` 决议（路径 D：放弃全站 heading 差异化） | spec/MASTER 文档修订 + token 清理 |
| H2 | types feature 整套英文字段标识符替换为中文 UI 文案 | UI 文案修订 |
| H3 | CheckoutTimeline 状态色改用 status-in-use token | className 修订 |
| H4 | TypesPage 空态接入 `<EmptyState>` 公共组件 | 组件复用 |
| H5 | NotFoundPanel 提到 `components/feedback/`，类型详情页接入 | 组件抽象（C 路径：feature wrapper） |
| M2 | 抽 `<SectionTitle>` + `<SectionCaption>` 双组件，替换 5 处复制 | 组件抽象（B 路径：拆两个） |

**显式不包括**：

- M1 TypesTable 接 stagger / tbody-fade
- M3 page-title type scale 统一
- M4 `transition-shadow` → `transition`
- 审计报告中标记为"已落地的设计强项"列表里的任何项（保留现状）
- 详情页 reading-mode `<h2>` 系列（`通用字段` / `附件` / `流转记录`）的 SectionHeading 替换——它们已是统一形态，本 PR 不引入额外 churn

未选项登记到 [`simplify-followups.md` §7](../simplify-followups.md#7-m2-视觉收尾审计未选项2026-05-03)，M3 规划时纳入考虑。

---

## 2 设计决议

### 2.1 H1 · `--font-heading` 决议（D 路径）

**问题**：`globals.css:11-13` 把 `--font-sans` 与 `--font-heading` 都设置为 Fira Sans，但 spec §3.5 + MASTER §Typography 都明文承诺 "Heading: Fira Code"。承诺与代码不一致已 6 个月。

**决议**：放弃"Heading 字体差异化"，承认现状即正确。

**视觉验证**：brainstorm 阶段做了 4 方案对比 mockup（`.superpowers/brainstorm/.../font-comparison*.html`）。关键观察：

- Fira Code **不渲染中文**，UI 中所有 heading（"小组资产管理工具" / "通用字段" / "基本信息"）都是中文，fallback 到 PingFang
- 唯一能看到 Fira Code 效果的是英文 h1（如资产名"Dell XPS 15 9530"）；Fira Code 等宽渲染 Latin 标题观感过于工业化
- "全 heading 切 Fira Code"（路径 A）和"仅品牌字"（路径 C）在实际界面上几乎无视觉差异

**实施动作**：

1. `frontend/src/styles/globals.css` 删除 `--font-heading` token（与 `--font-sans` 重复）。**注**：实施期 code review 发现 3 处 shadcn 组件 `DialogTitle` / `CardTitle` / `AlertDialogTitle` 之前用 `font-heading` Tailwind utility，token 删除后它们 fallback 到 `--font-sans`（视觉无变化）；本 Task 同步把这 3 处 className 显式改为 `font-sans`，避免 dead CSS var 引用
2. `docs/superpowers/specs/2026-04-24-m2c1-frontend-foundation-and-list-design.md` §3.5.3 字体合规节修订 "Heading 字体" 条目（行 98）：从 "Heading 字体 | Fira Code（Variable 优先） | 标题、asset_code 等编号字段" 改为 "Heading 字体 | Fira Sans（与 Body 同字型） | 标题层级靠字号区分；Fira Code 仅用于 mono 字段（asset_code / SN / code_prefix / 时间戳 / 显式 `.font-code` 标记位置）"
3. `design-system/asset-hub/MASTER.md` §Typography "Heading Font" 同步改为 Fira Sans，加注 "原 Fira Code 决议见 2026-05-03 视觉收尾纠偏"
4. AppLayout brand "小组资产管理工具" 不切 Fira Code（D 路径不引入 utility）

**不改动**：所有 h1/h2/h3 现有 className（保持 `font-medium` / `font-semibold` 等纯 Sans 形态）；`.font-code` 已存在的 mono 应用点不动。

---

### 2.2 H2 · types feature 中文化

**问题**：`types-table.tsx`、`type-form.tsx`、`type-summary-card.tsx` 三处把字段标识符（`name` / `code_prefix` / `description` / `created_at` / `updated_at` / `custom_fields`）直接当 UI 文本，与资产端中文化（`COLUMN_LABELS`）不一致。同一用户在 `/` 看中文跳到 `/types` 看英文标识。

**决议**：替换为中文 UI 文案，保持 `code_prefix` 等字段在输入框内继续走 `font-mono` 视觉提示（"代号前缀"语义靠 label 中文表达，输入值仍是英文大写字母）。

**文案映射**：

| 字段标识 | 中文文案 |
|---|---|
| name | 名称 |
| code_prefix | 代号前缀 |
| description | 描述 |
| created_at | 创建时间 |
| updated_at | 更新时间 |
| 字段数（已是中文，types-table.tsx 已用） | （不动） |
| 资产引用（已是中文） | （不动） |

**实施动作**：

1. `types-table.tsx` 列定义的 `header: 'name'` / `'code_prefix'` 改为中文
2. `type-form.tsx` `<FormLabel>name *</FormLabel>` / `<FormLabel>code_prefix *</FormLabel>` / `<FormLabel>description</FormLabel>` 改为 "名称 *" / "代号前缀 *" / "描述"
3. `type-summary-card.tsx` 5 个 `<dt>` 改为中文
4. `type-form.tsx` 提示文本 "创建后不可修改" 不动（已是中文）

**测试影响**：`tests/hooks/type-form.test.tsx` 等如断言了英文 label 文本会失败，同步改测试断言（不新增）。

---

### 2.3 H3 · CheckoutTimeline 状态色改 token

**问题**：`checkout-timeline.tsx:57` 写 `bg-[var(--status-active,#16a34a)]/10 text-[var(--status-active,#16a34a)]`。`--status-active` 在 `globals.css` 中**从未定义**，每次都回落到 hex `#16a34a`（emerald-600）。绕开了 OKLCH token 体系，dark 模式下色相对比偏离设计。

**决议**：改用已存在的 `--status-in-use` 系列 token（语义最接近："派发中" ≈ "在用"）。

**实施动作**：

```diff
- className="shrink-0 rounded-sm bg-[var(--status-active,#16a34a)]/10 px-2 py-0.5 text-xs font-medium text-[var(--status-active,#16a34a)]"
+ className="shrink-0 rounded-sm bg-status-in-use px-2 py-0.5 text-xs font-medium text-status-in-use-fg"
```

注：原 `/10` 透明度暗示色块淡。`--status-in-use` 已是 OKLCH 浅绿（`oklch(0.92 0.08 155)`），无需再做 `/10` 调淡——直接 `bg-status-in-use` 即可。dark 模式 `--status-in-use` 用 `oklch(0.28 0.08 150)` 暗绿，对比正确。

**不引入新 token**：不为"派发中"单独建 `--status-active`。spec §14.1 派出类型扩展（M3）若区分"派发中 / 出借中"等子状态，再开新 token。

---

### 2.4 H4 · TypesPage 空态接入 EmptyState

**问题**：`types-page.tsx:37-45` 内联 `flex flex-col items-center gap-3 py-16 text-muted-foreground` + `Inbox` icon + `<Button asChild>`，与 `components/feedback/empty-state.tsx` 视觉骨架重复。

**实施动作**：

```diff
- {q.data && q.data.length === 0 && (
-   <div className="flex flex-col items-center gap-3 py-16 text-muted-foreground">
-     <Inbox className="h-10 w-10" />
-     <p>还没有类型</p>
-     <Button asChild>
-       <Link to="/types/new">创建第一个类型</Link>
-     </Button>
-   </div>
- )}
+ {q.data && q.data.length === 0 && (
+   <EmptyState
+     title="还没有类型"
+     description="先创建一个类型，再为该类型登记资产"
+     action={
+       <Button asChild>
+         <Link to="/types/new">创建第一个类型</Link>
+       </Button>
+     }
+   />
+ )}
```

`Inbox` import 不再需要、删除。

---

### 2.5 H5 · NotFoundPanel 公共化（C 路径）

**问题**：`assets/detail/not-found-panel.tsx` 是 asset-private 实现；`type-detail-page.tsx:21-31` 内联复制了同款 `flex flex-col items-center gap-3 py-16` + `SearchX` icon + 返回按钮。M3 加第 3 个详情页前必须收敛。

**决议**：C 路径——公共 `<NotFoundPanel>` 接受最通用的 `backLink: ReactNode` slot，不绑 TanStack Router typed `<Link>`，不假设 search params。各 feature 写 thin wrapper 承载 typed Link。

**新文件结构**：

```
components/feedback/
  not-found-panel.tsx         (公共，~25 行)
features/assets/detail/
  asset-not-found.tsx         (新增，~10 行 thin wrapper)
  not-found-panel.tsx         (删除)
  asset-detail-page.tsx       (改 import: NotFoundPanel → AssetNotFound)
features/types/detail/
  type-not-found.tsx          (新增，~10 行 thin wrapper)
  type-detail-page.tsx        (内联 404 块替换为 <TypeNotFound />)
```

**公共组件 API**：

```tsx
// components/feedback/not-found-panel.tsx
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
      role="status"
      className="flex flex-col items-center gap-3 py-16 text-muted-foreground"
    >
      <Icon className="h-10 w-10" aria-hidden />
      <div className="space-y-1 text-center">
        <p className="text-base font-medium text-foreground">{title}</p>
        {description ? <p className="text-sm">{description}</p> : null}
      </div>
      <div className="mt-2">{backLink}</div>
    </div>
  );
}
```

**Wrapper 示例**：

```tsx
// features/types/detail/type-not-found.tsx
import { Link } from "@tanstack/react-router";
import { Button } from "@/components/ui/button";
import { NotFoundPanel } from "@/components/feedback/not-found-panel";

export function TypeNotFound() {
  return (
    <NotFoundPanel
      title="该类型不存在"
      description="可能已被删除，或链接错误"
      backLink={
        <Button asChild variant="outline">
          <Link to="/types">返回类型列表</Link>
        </Button>
      }
    />
  );
}
```

资产端 wrapper 同理，`backLink` 内传 typed `<Link to="/" search={ASSETS_DEFAULT_SEARCH}>`。

**为什么不让公共组件自己接 typed Link**：TanStack Router strict typing 要求 `to` + `search` 字面量绑定，公共组件想接 typed backTo 会引入泛型/cast，反而让 NotFoundPanel 变重。两个 thin wrapper 加起来不到 20 行，把"我要跳哪里 + 带什么 search"留在 feature 内部最清爽。

---

### 2.6 M2 · SectionHeading 抽象（B 路径）

**问题**：simplify §W 登记的 5 处复制（`type-form.tsx ×2`、`asset-form-fields.tsx`、`custom-fields-form.tsx`、`type-detail-page.tsx`）：

```tsx
className="text-sm font-semibold uppercase tracking-wide text-foreground border-b pb-1.5"
```

详情页另外有 3 处（`general-fields.tsx`、`attachment-grid.tsx`、`checkout-timeline.tsx`）使用 `mb-3 text-lg font-medium` 形态，**两种形态使用语境完全不重叠**：表单/元信息密度区用 caption，详情阅读区用 reading-mode。

**决议**：B 路径——拆两个组件 `<SectionTitle>` + `<SectionCaption>`，名字直接表语义。本 PR **只替换 caption 形态的 5 处**；reading-mode 形态保持现状（已统一、不引入额外 churn）。

**新组件**：

```tsx
// components/ui/section-heading.tsx
import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

interface Props {
  children: ReactNode;
  className?: string;
}

/** 详情阅读区 section 标题（GeneralFields / AttachmentGrid / CheckoutTimeline 风格） */
export function SectionTitle({ children, className }: Props) {
  return (
    <h2 className={cn("mb-3 text-lg font-medium", className)}>{children}</h2>
  );
}

/** 表单 / 元信息密度区 section caption（小写中文也走 uppercase 是英文场景下的设计姿态，
 *  CJK 字符上 `text-transform: uppercase` 无效，不影响中文渲染） */
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

**替换点**（5 处 caption）：

1. `features/types/form/type-form.tsx:131` "基本信息"
2. `features/types/form/type-form.tsx:192` "自定义字段"
3. `features/assets/form/asset-form-fields.tsx:41` （现 className）
4. `features/assets/form/custom-fields-form.tsx:21`
5. `features/types/detail/type-detail-page.tsx:47` "元信息"

**reading-mode 不替换**：`general-fields.tsx`、`attachment-grid.tsx`、`checkout-timeline.tsx` 的 `<h2 className="mb-3 text-lg font-medium">` 保留原样，本 PR 不动。如果未来发现这三处需要统一调整 className，再启动一次"replace-only"小 PR。

---

## 3 文档动作

### 3.1 spec / MASTER 修订

- `docs/superpowers/specs/2026-04-15-asset-hub-design.md` §3.5 "Heading 字体" 条目（H1）
- `design-system/asset-hub/MASTER.md` §Typography "Heading Font" 字段 + 实施期纠偏新增 "M2 视觉收尾（2026-05-03）" 节，回写 H1/H2/H3/H5/M2 决议

### 3.2 followup 登记

`docs/superpowers/simplify-followups.md` 新增 §7（实际写入内容如下，本 spec 一并给出避免 reviewer 来回查阅）：

```markdown
## §7 M2 视觉收尾审计未选项（2026-05-03）

**视角**：frontend-design skill 对照 ui-ux-pro-max MASTER + spec §3.5 做的 M2 阶段全栈审计；本 PR（M2 视觉收尾）闭环了 H 类全部 + M2 SectionHeading，以下是当时记录暂不动的项。

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

**ROI**：中。固化"列表/详情 h1 字号约定"防新增页面再加第 4 档；改动 trivial（约 5 行）。

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

`docs/superpowers/followup-allocation.md` §M3 强搭车表加一行：

```markdown
| **M2 视觉审计未选项** | simplify §7 | M3 启动时一并扫一遍（M1 motion / M3 type scale / M4 transition prop） |
```

---

## 4 测试 / 验证

**测试策略**：A 路径——不加新单元测试，跑现有 testsuite。

- `pnpm --dir frontend test --run` 全绿
- `pnpm --dir frontend lint` + `pnpm --dir frontend exec tsc -b` 0 错误
- `uv run pytest` 不受影响（纯前端 PR）
- 现有 vitest 如断言英文 label 文本（H2 改后会失败），同步改断言**不新增**测试

**手工烟测**（合并前 dev server 走一遍）：

| 场景 | 验证点 |
|---|---|
| `/` 资产列表 → 点资产名进详情 | 详情页所有 h2 仍正常显示（reading-mode 未动） |
| `/` 资产列表 → 派出资产 → 看 timeline | "派发中" pill 颜色用 token，浅模式柔和绿、深模式深绿 |
| `/types` 列表（数据为 0） | 显示 EmptyState 三段（icon + title + description + button） |
| `/types/new` 表单 | label "名称 *" / "代号前缀 *" / "描述"，section caption "基本信息" / "自定义字段" 中文 + uppercase |
| `/types/$id` 编辑页 | "元信息" caption 中文；TypeSummaryCard `<dt>` 全中文 |
| `/types/00000000-...`（不存在 UUID） | 404 态显示 "该类型不存在"，按钮跳 `/types` |
| `/assets/00000000-...`（不存在 UUID） | 404 态显示资产专属文案 + 按钮跳 `/`（含 search params） |
| 切深色模式重做以上 | 状态色 / 文本对比不退化 |

**红线扫描**（合并前最后一次执行）：

```bash
grep -rnE 'scale-|animate-spin|backdrop-blur|bg-gradient-to|font-family.*Inter|font-family.*Roboto|font-family.*Geist' frontend/src/
```

预期 0 命中。

---

## 5 风险

| 风险 | 概率 | 影响 | 缓解 |
|---|---|---|---|
| H2 中文化漏改某处导致英文标识符仍残留 | 低 | 视觉漂移 | 合并前 grep `'name'`/`'code_prefix'` 在 types feature 检查残留 |
| H3 状态色改 token 后视觉变化超出预期 | 低 | 用户感知"派发中"色调变化 | dev server 浅/深模式各看一遍；如视觉不满意可调用 `/40` 透明度兜底 |
| H5 thin wrapper 加 2 个文件后 simplify §U "trigger fire" 状态难判断 | 极低 | 文档维护 | §U 在 simplify-followups.md 直接标 ✅ 闭环（commit ref） |
| M2 SectionCaption `text-transform: uppercase` 在中文 "基本信息" 上无效 | 已知 | 无 | 设计本就如此（中文不响应 uppercase，留给英文场景） |

---

## 6 实施顺序

按依赖关系：

1. **H1 文档修订**（spec + MASTER），删 `--font-heading` token —— 先做最低风险
2. **H4 TypesPage EmptyState**（独立、最简单）
3. **H3 timeline token**（1 行修改）
4. **M2 SectionHeading 组件**（先建组件，不替换调用点）
5. **H2 types 中文化**（替换 3 处文本）
6. **M2 替换 5 处 caption** 调用点
7. **H5 NotFoundPanel 公共化**（建公共组件 + 2 个 wrapper + 替换 2 处调用 + 删 asset 旧文件）
8. **MASTER 实施期纠偏 + simplify-followups §7 + followup-allocation 登记**
9. **手工烟测 + 红线扫描 + 跑测试套件**

**预计**：单 PR 一次提交（或拆 7-8 个 commit 在同 PR 内）。规模 ~120 行 diff，1 次 review pass 可完成。

---

## 7 决策来源

| 决策 | 选项 | 选定 | 理由（节选） |
|---|---|---|---|
| Q1 PR 范围 | A 紧 / B 中 / C 全包 | **B** | M3 启动前还设计契约欠款 |
| Q2 字体决议 | A 全切 Code / B utility / C 仅 brand / D 全 Sans | **D** | 视觉对比表明三方案在中文 UI 下几乎无差异，承认现状最低成本 |
| Q3 SectionHeading | A variant / B 拆两个 / C 只抽 className | **B** | 两 variant 使用语境完全不重叠 |
| Q4 NotFoundPanel | A 全参数 / B 适度 / C slot + wrapper | **C** | TanStack Router strict typing 不外泄 |
| Q5 followup 登记 | A simplify §7 / B 新文件 / C followup-allocation | **A** | 单一 followup 索引，M3 brainstorm 一次扫干净 |
| Q6 测试 | A 不加新测 / B 加组件测 / C +文案断言 | **A** | 字符串/className 改动加单测 ROI 低，预算留给 simplify §R |

---

## 8 后续

PR 合并后：

- M3 brainstorm 启动时阅读 `simplify-followups.md` §7 + `followup-allocation.md` 决定 M1/M3/M4 是否搭车
- 设计契约审计**作为流程留存**：今后每个里程碑合并后由作者主动跑一次 frontend-design 审计，审计报告对应未闭环项进 simplify-followups.md 新增 §N

不在本 PR 范围的所有审计已落地强项（color token / OKLCH dark 独立调 / Motion 三时刻 / focus-visible / anti-pattern 红线 / Empty/Error/Loading 三态 / 等）保留现状。
