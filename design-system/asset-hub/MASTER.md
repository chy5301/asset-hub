# Design System Master File

> **LOGIC:** When building a specific page, first check `design-system/pages/[page-name].md`.
> If that file exists, its rules **override** this Master file.
> If not, strictly follow the rules below.

---

**Project:** asset-hub
**Generated:** 2026-04-23 23:36:33
**Category:** Analytics Dashboard

---

## Global Rules

### Color Palette

| Role | Hex | CSS Variable |
|------|-----|--------------|
| Primary | `#1E40AF` | `--color-primary` |
| Secondary | `#3B82F6` | `--color-secondary` |
| CTA/Accent | `#F59E0B` | `--color-cta` |
| Background | `#F8FAFC` | `--color-background` |
| Text | `#1E3A8A` | `--color-text` |

**Color Notes:** Blue data + amber highlights

### Chart 6 槽 token (M3b 看板用)

| Token | Hue | 用途 |
|---|---|---|
| `--chart-1` | 240° (蓝) | 类型分布派色槽 1 |
| `--chart-2` | 30° (橙) | 类型分布派色槽 2 |
| `--chart-3` | 145° (绿) | 类型分布派色槽 3 |
| `--chart-4` | 80° (黄) | 类型分布派色槽 4 |
| `--chart-5` | 280° (紫) | 类型分布派色槽 5 |
| `--chart-6` | 0° (红) | 类型分布派色槽 6 |

亮度/饱和度统一: light `oklch(0.7 0.13 <hue>)` / dark `oklch(0.62 0.13 <hue>)`;
6 槽相邻 hue 差 ≥ 60° 防刺眼撞色; 同一 type 按 type_id 第一字符 charCode % 6 哈希到稳定槽位.

### Status token（状态语义色）

| Token | 色相描述 | 用途 |
|---|---|---|
| `--status-in-use` | 绿色，hue ≈ 150° | IN_USE 状态 chip / 背景 |
| `--status-in-use-fg` | 同色相深 fg | IN_USE chip 文字色 |
| `--status-idle` | 中性蓝灰，hue ≈ 247° | IDLE 状态 chip / 背景 |
| `--status-idle-fg` | 同色相深 fg | IDLE chip 文字色 |
| `--status-maintenance` | 橙黄，hue ≈ 65° | MAINTENANCE 状态 chip / 背景 |
| `--status-maintenance-fg` | 同色相深 fg | MAINTENANCE chip 文字色 |
| `--status-broken` | 红橙，hue ≈ 30°（v2.0） | BROKEN 状态 chip / 背景 |
| `--status-broken-fg` | 同色相深 fg（v2.0） | BROKEN chip 文字色 |
| `--status-retired` | 蓝灰，hue ≈ 247° | RETIRED 状态 chip / 背景 |
| `--status-retired-fg` | 同色相深 fg | RETIRED chip 文字色 |
| `--status-disposed` | 纯灰，chroma=0 | DISPOSED 状态 chip / 背景（无色相） |
| `--status-disposed-fg` | 同灰深 fg | DISPOSED chip 文字色 |
| `--status-borrowed`    | 琥珀（amber），hue ≈ 75°  | CHECKOUT_EXTERNAL（对外出借）chip / Group rail external |
| `--status-borrowed-fg` | 同色相深 fg              | 上同 chip 文字色                                        |
| `--warning`            | amber 黄，hue ≈ 90°      | due-soon 黄色警示（< 7 天到期）                         |
| `--warning-fg`         | 同色相深 fg              | warning 文字色 / 角标 fg                                |

light/dark 独立调（不做反转），双套落地于 `globals.css` `:root` + `.dark` + `@theme inline` 映射。

**status-broken**（v2.0）：用于资产"故障"态 chip / badge / chart slice。Light H=30 红橙色调（`oklch(0.93 0.13 30)` bg / `oklch(0.42 0.18 28)` fg），与 status-maintenance（H=65 橙黄）保持 35° hue 距离避免视觉混淆。Dark 模式 `oklch(0.32 0.13 25)` bg / `oklch(0.82 0.15 30)` fg，保持区分度。XLSX 导出 hex：`FFFCCFC1`（`#FCCFC1`，oklch(0.93 0.13 30) 的近似 sRGB）。

### Dashboard Atmosphere

| Token | 用途 |
|---|---|
| `--dashboard-bg-radial-from` | radial gradient 起点 (顶部 50% 20%) |
| `--dashboard-bg-radial-to` | radial gradient 终点 (向外铺) |

替代 solid 背景, light 模式偏白发光, dark 模式深蓝氛围.

### Typography

- **Heading Font:** Fira Sans（M2 视觉收尾纠偏，2026-05-03；原承诺 Fira Code，但 Fira Code 不渲染中文，全 fallback 到 PingFang，差异化无效；mono 字段保留 Fira Code）
- **Body Font:** Fira Sans
- **Mono Font:** Fira Code（asset_code / SN / code_prefix / 时间戳 / `.font-code`）
- **Mood:** dashboard, data, analytics, code, technical, precise
- **Google Fonts:** [Fira Code + Fira Sans](https://fonts.google.com/share?selection.family=Fira+Code:wght@400;500;600;700|Fira+Sans:wght@300;400;500;600;700)

**CSS Import:**
```css
@import url('https://fonts.googleapis.com/css2?family=Fira+Code:wght@400;500;600;700&family=Fira+Sans:wght@300;400;500;600;700&display=swap');
```

### Spacing Variables

| Token | Value | Usage |
|-------|-------|-------|
| `--space-xs` | `4px` / `0.25rem` | Tight gaps |
| `--space-sm` | `8px` / `0.5rem` | Icon gaps, inline spacing |
| `--space-md` | `16px` / `1rem` | Standard padding |
| `--space-lg` | `24px` / `1.5rem` | Section padding |
| `--space-xl` | `32px` / `2rem` | Large gaps |
| `--space-2xl` | `48px` / `3rem` | Section margins |
| `--space-3xl` | `64px` / `4rem` | Hero padding |

### Shadow Depths

| Level | Value | Usage |
|-------|-------|-------|
| `--shadow-sm` | `0 1px 2px rgba(0,0,0,0.05)` | Subtle lift |
| `--shadow-md` | `0 4px 6px rgba(0,0,0,0.1)` | Cards, buttons |
| `--shadow-lg` | `0 10px 15px rgba(0,0,0,0.1)` | Modals, dropdowns |
| `--shadow-xl` | `0 20px 25px rgba(0,0,0,0.15)` | Hero images, featured cards |

---

## Component Specs

### Buttons

```css
/* Primary Button */
.btn-primary {
  background: #F59E0B;
  color: white;
  padding: 12px 24px;
  border-radius: 8px;
  font-weight: 600;
  transition: all 200ms ease;
  cursor: pointer;
}

.btn-primary:hover {
  opacity: 0.9;
  transform: translateY(-1px);
}

/* Secondary Button */
.btn-secondary {
  background: transparent;
  color: #1E40AF;
  border: 2px solid #1E40AF;
  padding: 12px 24px;
  border-radius: 8px;
  font-weight: 600;
  transition: all 200ms ease;
  cursor: pointer;
}
```

### Cards

```css
.card {
  background: #F8FAFC;
  border-radius: 12px;
  padding: 24px;
  box-shadow: var(--shadow-md);
  transition: all 200ms ease;
  cursor: pointer;
}

.card:hover {
  box-shadow: var(--shadow-lg);
  transform: translateY(-2px);
}
```

### Inputs

```css
.input {
  padding: 12px 16px;
  border: 1px solid #E2E8F0;
  border-radius: 8px;
  font-size: 16px;
  transition: border-color 200ms ease;
}

.input:focus {
  border-color: #1E40AF;
  outline: none;
  box-shadow: 0 0 0 3px #1E40AF20;
}
```

### Modals

```css
.modal-overlay {
  background: rgba(0, 0, 0, 0.5);
  backdrop-filter: blur(4px);
}

.modal {
  background: white;
  border-radius: 16px;
  padding: 32px;
  box-shadow: var(--shadow-xl);
  max-width: 500px;
  width: 90%;
}
```

---

## Style Guidelines

**Style:** Data-Dense Dashboard

**Keywords:** Multiple charts/widgets, data tables, KPI cards, minimal padding, grid layout, space-efficient, maximum data visibility

**Best For:** Business intelligence dashboards, financial analytics, enterprise reporting, operational dashboards, data warehousing

**Key Effects:** Hover tooltips, chart zoom on click, row highlighting on hover, smooth filter animations, data loading spinners

### Page Pattern

**Pattern Name:** Portfolio Grid

- **Conversion Strategy:**  hover overlay info,  lightbox view, Visuals first. Filter by category. Fast loading essential.
- **CTA Placement:** Project Card Hover + Footer Contact
- **Section Order:** 1. Hero (Name/Role), 2. Project Grid (Masonry), 3. About/Philosophy, 4. Contact

---

## Anti-Patterns (Do NOT Use)

- ❌ Ornate design
- ❌ No filtering

### Additional Forbidden Patterns

- ❌ **Emojis as icons** — Use SVG icons (Heroicons, Lucide, Simple Icons)
- ❌ **Missing cursor:pointer** — All clickable elements must have cursor:pointer
- ❌ **Layout-shifting hovers** — Avoid scale transforms that shift layout
- ❌ **Low contrast text** — Maintain 4.5:1 minimum contrast ratio
- ❌ **Instant state changes** — Always use transitions (150-300ms)
- ❌ **Invisible focus states** — Focus states must be visible for a11y

---

## Pre-Delivery Checklist

Before delivering any UI code, verify:

- [ ] No emojis used as icons (use SVG instead)
- [ ] All icons from consistent icon set (Heroicons/Lucide)
- [ ] `cursor-pointer` on all clickable elements
- [ ] Hover states with smooth transitions (150-300ms)
- [ ] Light mode: text contrast 4.5:1 minimum
- [ ] Focus states visible for keyboard navigation
- [ ] `prefers-reduced-motion` respected
- [ ] Responsive: 375px, 768px, 1024px, 1440px
- [ ] No content hidden behind fixed navbars
- [ ] No horizontal scroll on mobile

---

## 实施期纠偏（M2c-1，2026-04-24）

`frontend-design` skill 合并前审查 + 手工烟测（spec 附录 A 15 项 + Pre-Delivery Checklist 7 项）通过后，以下纠偏项回写备查。基础审美承诺（§3.5）全部兑现；以下是**实施期发现的上游缺口**与**临时权宜**：

### 1. 后端 `AssetRead` DTO 缺 `asset_code` 字段（M1 骨架遗漏）

**现象**：spec §5.1 设计"asset_code 内部编号"为资产主识别符（列表第二列），但后端 ORM `Asset` 模型 + `AssetRead` DTO 都未实现此字段。

**权宜**：M2c-1 前端把"编号列"改成"**代号**"，显示 `serial_number ?? id.slice(0, 8)`——用铭牌号（SN）作主识别符，无 SN 时回落到 UUID 前 8 位。等宽字体（`font-code` / Fira Code）保留。

**待办**（推到 M3，优先级：高）：
- `Asset` 模型 + `AssetCreate/Read` DTO 补 `asset_code: str`（`unique=True, index=True`）
- Service 层实现自动生成规则：`<type_prefix>-<year>-<序号>`（spec §5.1 已设计）
- `AssetType` 可能需要加 `code_prefix` 字段（用于前缀推导）
- CLI `asset register` 加可选 `--code` 参数
- DB 迁移（已有数据按某种规则回填）

### 2. 后端 `AssetRead` DTO 缺 `type_name` 字段（同类缺口）

**现象**：AssetRead 只暴露 `type_id`（UUID）。若直接显示会是 UUID，信息量为零。

**权宜**：前端在 `routes/index.tsx` 用 `useAssetTypesQuery` 取全量类型字典，客户端 `type_id → type_name` join 后传给 `<AssetsTable typeNameById={...}>`。单用户场景类型数极少（<20），client-side join 开销微乎其微。

**待办**（M3，优先级：中）：
- `AssetRead` 可加 `type_name: str | None`（SQLAlchemy relationship 懒加载 + Pydantic computed/attribute）
- 或保留当前客户端 join 方案（足够、可接受）——如保留则此项可关

### 3. Fira Sans 无 variable font 发布（npm 生态事实）

**现象**：`@fontsource-variable/fira-sans` 在 npm 上 404；只有 Fira Code 有 variable。

**权宜**：本里程碑统一用 `@fontsource/*`（静态字体包）。Bundle 相比理论最优 variable 方案增大 ~100KB。`font-family` 字面量去掉 `Variable` 后缀，不影响渲染。

**待办**（M4 UI 打磨期，优先级：低）：
- 评估是否混用 `@fontsource-variable/fira-code` + `@fontsource/fira-sans`——优点：mono 字段 bundle 更小；代价：两种包约定并存
- 或等 Fira Sans 官方出 variable 再切

### 4. `openapi-typescript@7.x` 声明 peer `typescript: "^5.x"` 但项目用 TS 6.0.2

**现象**：pnpm install 有 peer-dep warning；实际 binary 在 TS 6 环境下正常加载与生成（M2c-1 Task 3 已冒烟验证）。

**权宜**：接受 warning，不动。

**待办**（持续观察，优先级：低）：
- `openapi-typescript` 若出 8.x 支持 TS 6.x，`pnpm up openapi-typescript@latest`
- 如未来真因 TS 新特性导致运行时错误，降 TypeScript 到 5.x（但要评估 TanStack Router 的 strictNullChecks 是否仍正常）

### 5. shadcn scaffold 默认带 Next.js `"use client"` 指令 + `next-themes` 依赖

**现象**：Task 2 `pnpm dlx shadcn@latest add sonner` 等生成的组件包含 Next-only 残留（已在 Task 12 清理）。

**权宜**：Task 12 已修——sonner 改用项目自己的 `@/components/theme/theme-provider` 的 `useTheme`；"use client" 指令从 separator / sonner / table 首行移除。后续 shadcn CLI 新增组件时需**手动重复此审查**（§3.5.7 红线：每次 add 必须同 PR 内完成 variant 审查）。

**待办**（流程，优先级：低）：
- 若 shadcn CLI 后续支持"Vite-native" profile，切换配置避免生成 Next 残留

### 6. pnpm workspace 空警告（环境级，不阻塞）

**现象**：`pnpm install` 偶尔提示 `pnpm-workspace.yaml` 空。

**权宜**：不处理。asset-hub 是单包项目，`pnpm-workspace.yaml` 是历史遗留文件。

---

## frontend-design Pre-Delivery Checklist（M2c-1 验证）

- [x] No emojis as icons（全用 Lucide SVG：Inbox / AlertTriangle / Sun / Moon / Laptop / Settings2 / MoreHorizontal / Circle / CircleDot / Wrench / MinusCircle / ChevronLeft / ChevronRight / ArrowUp / ArrowDown / ArrowUpDown）
- [x] cursor-pointer on clickable elements（shadcn Button 默认；表格行 `cursor-pointer` 显式）
- [x] Hover transitions smooth 150-300ms（`transition-colors`；无 `transform: scale`）
- [x] Light mode text contrast 4.5:1 minimum（navy-900 on slate-50 ≈ 13:1 muted-foreground on bg ≈ 5:1；状态 pill 按色相对对）
- [x] Focus states visible for keyboard（globals.css `*:focus-visible { outline: 2px solid var(--ring); outline-offset: 2px }`）
- [x] `prefers-reduced-motion` respected（globals.css 媒体查询降级 stagger / tbody-fade / transition-duration）
- [x] Responsive 1024+（max-width 1400px；<1024 会横向滚动，M4 polish 期再响应式）

手工烟测通过项（spec 附录 A）：1 (EmptyState) / 3 (URL sync) / 4 (刷新保留筛选) / 5 (改筛选回第 1 页) / 7 (主题切换无闪烁) / 13 (字体审计 `Fira Sans` + `Fira Code`，无 Inter/Roboto/Geist)。

其余项目（backend kill→ErrorState；>2000 条 console.warn；Motion 三时刻 Perf 录制；Lighthouse a11y Score）由 Task 级 review 在实施期逐 Task 已验证，或已在代码路径静态可见（`if (query.isError)` + `<ErrorState onRetry={refetch}>`）。


---

## 实施期纠偏（M2c-2，2026-04-25）

`frontend-design` skill 合并前审查（spec §3.3 闸门 ②③）+ Pre-Delivery Checklist 7 项 + 红线扫描 0 命中后回写。M2c-1 纠偏项（后端 `asset_code` / `type_name` 缺口）仍保留；以下是 M2c-2 新增的记录。

### 1. MASTER 显式 override 清单（兑现 spec §3.4.1）

本里程碑对 MASTER 做了以下覆盖，理由已在 spec §3.4.1 记录：

- **`Key Effects: data loading spinners` → 改用按钮文字切换 + 骨架**：mutation pending 时按钮文字切到「派发中…」「归还中…」「删除中…」（来自 `checkout-actions.ts` 常量）；query loading 用 `DetailSkeleton` / `GridSkeleton` / `TimelineSkeleton`。spinner 是 AI-slop 重灾区。
- **`Modal backdrop-filter: blur(4px)` → 改 `bg-black/50` 不 blur**（dialog.tsx / alert-dialog.tsx Overlay）。glassmorphism overused。
- **`Card: box-shadow + hover translateY` → 详情页不用 Card 装饰**：所有区块用 `<dl>` / `<ol>` / 自绘 timeline；timeline 卡片仅 `ring-1 ring-border/60` 无 shadow、无 hover 位移。fewer-but-better；hover 位移与 MASTER 自己的 anti-pattern #3 矛盾。
- **`<Separator>` 未使用**：spec §7.1 决定 `space-y-10` + 各 section `<h2>` 语义分区即可。

### 2. Timeline 视觉：合并前 polish 去节点 + status pill 文字化

**原方案**：左侧 vertical line + 圆点节点（实心绿当前 / 空心 muted 历史）+ 右上 "进行中" pill。

**polish 后（A Hybrid 形态，提交于 M2c-2 合并 buffer 期）**：
- 删除 vertical line + 圆点节点（与详情页其他区块的 dl/section 视觉调性不一；状态信息已由 pill 表达，圆点为冗余——违反 §3.5.1 fewer-but-better）
- 卡片改 flat-stack `space-y-3`
- 进行中卡右上角 pill `[派发中]`（`bg-status-active/10 text-status-active`）；已归还卡**不显示 pill**（整卡 muted 色调表达"过去了"，避免重复信息）
- 抽 `formatCheckoutStatus(checkout)` 纯函数，把 M3 派出类型分化点收敛到一处

**M3 仍待做的清单**（与主 doc §14.8 + spec §10.2 同源）：

- 时间近远渐隐（opacity 分级 ≤90d / ≤180d / 更早）
- 派出类型染色（与 §14.1 "向外出借"扩展联动；进行中卡片 pill 文字 "派发中" / "出借中"，已归还卡通过 ring 边框色保留派出类型线索）
- 超长派发预警（> 90 天未归还，节点加 `Clock` + `text-destructive`）

M3 启动时按此清单继续重构，不要重新讨论。

### 3. Dialog 表单用纯 React state（M2c-3 迁 RHF）

M2c-2 两个 Dialog（`CheckoutDialog` / `ReturnDialog`）用 `useState` + 手工校验实现，未引入 RHF+Zod。M2c-3 引入 Vitest + RHF + Zod 时，将把这两个 Dialog 迁到 RHF 版本（约半天工作量）。迁移只改表单状态 + 校验层，不动 JSX 骨架 / Toast / mutation hook。

M2c-3 plan 起笔时要求列为独立 Task，避免遗漏。

### 4. `useCheckoutHistoryQuery` 的 `enabled` 守护

列表页 ⋯ 菜单的 `ReturnDialog` 在 `returnRow === null` 时传 `assetId=""`。最初实现会对空字符串发 `/api/assets//history` 请求（404）。Task 17 已修：hook 加 `enabled: !!assetId`。

后续若新增更多"条件拉取"类的 query，遵循此模式。

### 5. `useDeleteAttachmentMutation` 不走 `unwrap`

DELETE 端点返回 204 无 body，`unwrap` 要求 `data` 存在会抛错。hook 内手工处理 `res.error` 即可，不改 `unwrap` 签名。throw 出去的错误对象用 `HttpErrorShape` 类型注解，与 `unwrap` 的抛错形态一致——这样 `isHttpError` / `toFriendlyMessage` 都能正确解析。

若后续新增更多 204 端点，可考虑给 `unwrap` 加一个 `allowEmpty` 选项；但单例不值当。

### 6. 新增运行时依赖：`date-fns`

spec §4.3 起草时误以为 M2c-1 已装 `date-fns`（实际 M2c-1 用的是原生 `Date.toLocaleString`），实施期 Task 4 发现缺漏并补装 `date-fns ^4.1.0`。这是 M2c-2 唯一的新增 npm runtime 依赖（~3kb gzipped 树摇后）。spec §4.3 已同步修正。

### Pre-Delivery Checklist（M2c-2 验证）

- [x] No emojis as icons（全 Lucide SVG：SearchX / Copy / Check / X / Download / Trash2 / FileText / FileImage / File / Paperclip 等）
- [x] cursor-pointer on clickable elements（shadcn Button 默认；附件缩略图 `<button>` 显式 `cursor-pointer`）
- [x] Hover transitions smooth 150-300ms（`transition-colors` / `transition-shadow`；无 `transform: scale`）
- [x] Light mode text contrast 4.5:1（M2c-1 已实测；本里程碑未引入新色变量，沿用 globals.css）
- [x] Focus states visible for keyboard（globals.css `*:focus-visible` 兜底；Dialog / AlertDialog 默认 focus trap；Input / textarea 显式 `focus-visible:ring-2 focus-visible:ring-ring`）
- [x] `prefers-reduced-motion` respected（globals.css 媒体查询降级 M2c-1 已设；本里程碑详情页本身不做 stagger，无依赖路径需要降级）
- [x] Responsive 1024+（max-width 960；<1024 附件宫格自动从 4 列降至 3/2 列；其他区块为单列纵向自然适配）

### 红线扫描结果

`grep -rn "scale-\|animate-spin\|backdrop-blur\|bg-gradient"` 在 M2c-2 新增 17 个文件 + 修改 4 个文件 + 新增 2 个 shadcn 组件内：**0 命中**。

### 手工烟测（spec 附录 A 12 项）

由作者在合并前在浏览器中逐项执行；本静态闸门已通过。

---

## 实施期纠偏（M2c-3，2026-04-27）

frontend-design 闸门 ②③ + Pre-Delivery Checklist 7 项 + 红线 0 命中后回写。承接 M2c-1 / M2c-2 已写入的覆盖清单。

### 1. M2c-1 / M2c-2 上游缺口"asset_code 字段"已落地

**M2c-1 实施期纠偏 §1**（"后端 AssetRead DTO 缺 asset_code 字段，权宜列表用 SN ?? id.slice(0, 8) 顶替"）状态：**M2c-3 已落地**。具体落地形态参考 M2c-3 spec §12 反向纠偏说明 + §1.1.2 / §5.1 / §7.9。

新形态：
- `Asset.asset_code` 自动生成 `{prefix}-{seq:03d}`（如 `NB-007`）
- `AssetType.code_prefix` 必填字段（`^[A-Z]{2,4}$`、unique、immutable）
- 列表第一列改回 asset_code（mono Fira Code），SN 拆为独立列

### 2. type_name 反规范化方式

**plan 决议**：SQLAlchemy `Relationship` + `lazy="joined"` + `Asset.type_name` `@property` 暴露。详见 `src/asset_hub/models/asset.py`。

- 单 SELECT 自动 JOIN，对单 asset 查询无 N+1
- list_assets 走默认 select(Asset)，relationship lazy=joined 兜底
- AssetRead DTO 通过 `from_attributes=True` 自动读取 `Asset.type_name` property

### 3. shadcn 新增组件 variant 审查清单

本里程碑首次引入 `form / checkbox / radio-group / select / popover / calendar / command / label`。引入即审：
- 全部移除 Next 残留 `"use client"` 指令
- Calendar 设 `locale={zhCN}`
- Select / Popover / Calendar 全部用 `bg-popover` token，未硬编码 `bg-white`

### 4. 表单 input padding override（与 MASTER baseline 不同）

MASTER 给的 `.input { padding: 12px 16px }` 是 hero/landing 风格；表单密度场景下 shadcn 默认 size="default"（更紧）更合适。本里程碑表单 input 沿用 shadcn 默认。

### 5. RHF 迁移已完成（M2c-2 留的债）

`CheckoutDialog` / `ReturnDialog` 从纯 React state 迁到 RHF + Zod，UX 行为前后一致。Vitest 2 case 试点用例已加。

### 6. 附件 add slot 视觉样式

MASTER 未涉及 dropzone 元素。本里程碑显式定义：
- 默认：`border: 1.5px dashed muted-foreground/40 + 圆角同 tile + transition-colors`
- hover：`border-primary text-primary bg-primary/5`
- 拖拽 active：同 hover
- 上传中：tile 内显示文件名 + 进度条（width transition），无 spinner
- 失败：destructive 文本 + 重试按钮（lucide `RotateCw`）

与 MASTER hover 用色温变化（不是 shadow / scale）同源。

### 7. 上传进度条用 width transition 而非 spinner

`AttachmentAddSlot` 的进度态用 `<div style={{ width: `${percent}%` }} className="transition-[width] duration-150 ease-out">`，避免 `animate-spin`。承接 M2c-2 反 AI-slop 红线。

### 8. wire format 决议：`key` 而非 `name`

M2c-3 spec D2 informal 用了 `name`，但实际 wire format **决议为 `key`**（与 M1/M2 老 fixtures + 后端 validation.py 一致）。FieldDef TS 类型 + 后端 CustomFieldDef Pydantic 都用 `key`。Task 2 review 期发现并 revert。

### 9. CLI flag 重命名

`type define` 的 prefix flag 在 Task 2 期间用了 `--code-prefix` 作为 transient，Task 9 统一改为 `--prefix`（与 plan 一致）+ 同步 11 处测试调用。

### 10. Alembic 首次引入 + post_write_hooks 不工作

M1 跳过 Alembic；M2c-3 首次引入。`alembic.ini` 配置的 `post_write_hooks = ruff_format` 在当前 Python 包环境下不工作（ruff 没注册 console_scripts entrypoint）——新生成 migration 文件后需手工 `uv run ruff format <文件>`。Follow-up 项。

### 11. Migration fallback prefix 派生用严格 ASCII regex

Task 8 实施期发现 Python `str.isalpha()` / `isupper()` 对 CJK 字符返回 True，导致 `笔记本电脑` 派生出 `笔X` 通过格式检查。修复：用 `re.fullmatch(r"^[A-Z]{2,4}$")` 严格守门。

### 12. mutation hook 测试推迟到 follow-up

Task 27 实施期发现 vitest 4 + jsdom + openapi-fetch 的 `Request` URL 解析问题导致 MSW 拦截失效（相对路径 `/api/...` 不能 `new Request()`）。CheckoutDialog 试点用 `vi.mock` 兜底；3 个 mutation hook 测（useCreateAsset / useDeleteAsset / useChangeAssetStatus）跳过待 `tests/setup.ts` 修复 URL 解析后统一补。

### Pre-Delivery Checklist（M2c-3 验证）

- [x] No emojis as icons（全 Lucide：Plus / X / RotateCw / AlertCircle / CalendarIcon / ChevronsUpDown / Check / MoreHorizontal）
- [x] cursor-pointer on clickable elements（shadcn Button / DropdownMenuItem 默认；AddSlot button 显式）
- [x] Hover transitions smooth 150-300ms（`transition-colors`，无 `transform: scale`）
- [x] Light mode text contrast 4.5:1（沿用 M2c-1 token，无新色）
- [x] Focus states visible for keyboard（globals.css 兜底；form / dialog 默认 focus-visible）
- [x] `prefers-reduced-motion` respected（沿用 globals.css 媒体查询；表单页本身无 stagger）
- [x] Responsive 1024+（max-w-2xl 表单；详情页继续 max-w-960）

### 红线扫描结果

`grep -rnE 'scale-|animate-spin|backdrop-blur|bg-gradient-to'` 在 M2c-3 新增/修改文件内：**0 命中**。

---

## 实施期纠偏（M2 视觉收尾，2026-05-03）

frontend-design skill 对 M2a→M2c-4 全栈做了一次设计契约对照审计（见 [`docs/superpowers/specs/2026-05-03-m2-visual-polish-design.md`](../../docs/superpowers/specs/2026-05-03-m2-visual-polish-design.md)）。本里程碑闭环 H 类全部 + M2 SectionHeading；以下是新写入的覆盖 / 决议。

### 1. H1 · 放弃 "Heading: Fira Code" 承诺（D 路径）

**原承诺**：MASTER §Typography "Heading Font: Fira Code"，spec m2c1 §3.5.3 字体合规表 "Heading 字体 Fira Code"。
**实际情况**：Fira Code 不渲染中文，UI 中所有 heading（"小组资产管理工具" / "通用字段" / "基本信息"）都走 PingFang fallback；唯一能见到 Fira Code 效果的是英文 h1（如资产名）；视觉对比表明三方案在中文 UI 下几乎无差异。
**决议**：删 `globals.css --font-heading` token，spec/MASTER 改成 "Heading: Fira Sans；Fira Code 仅用于 mono 字段"。
**实施**：M2 视觉收尾 PR Task 1，commit ref 见 git log。**code review 发现** 3 处 shadcn 组件（DialogTitle / CardTitle / AlertDialogTitle）之前用 `font-heading` Tailwind utility，token 删除后同步改为 `font-sans` 显式声明。

### 2. H2 · types feature UI 文本英文 → 中文

**问题**：types-table 表头 / type-form FormLabel / TypeSummaryCard `<dt>` 用 `name` / `code_prefix` / `description` 字段标识符当 UI 文本，与资产端中文化（COLUMN_LABELS）不一致。
**决议**：替换为 "名称 / 代号前缀 / 描述 / 创建时间 / 更新时间"；`code_prefix` 等字段在 input 内继续走 `font-mono`，"代号前缀" 语义靠中文 label 表达。
**实施**：M2 视觉收尾 PR Task 5。

### 3. H3 · CheckoutTimeline 状态色改 token

**问题**：`bg-[var(--status-active,#16a34a)]/10` 中 `--status-active` 从未定义，每次回落到 hex `#16a34a`，绕开 OKLCH dark-mode 独立调机制。
**决议**：改用已存在的 `--status-in-use` / `--status-in-use-fg` token；不为"派发中"单独建 `--status-active`。code review 发现 `custom-field-formatter.tsx` 同款 anti-pattern 一并清理。
**实施**：M2 视觉收尾 PR Task 3 + follow-up。

### 4. H4 · TypesPage 接 EmptyState

**问题**：内联 `flex flex-col items-center gap-3 py-16` + Inbox + Button 与公共 EmptyState 视觉骨架重复。
**决议**：改用 `<EmptyState title description action>`。
**实施**：M2 视觉收尾 PR Task 2。

### 5. H5 · NotFoundPanel 公共化（C 路径）

**问题**：asset-private NotFoundPanel + type-detail-page 内联同款骨架，2 倍化触发抽公共组件。
**决议**：lift 到 `components/feedback/not-found-panel.tsx`，接 `backLink: ReactNode` slot；assets/types 各写 thin wrapper 承载 typed Link。code review 同步修两点：role 改 `status`（与 EmptyState 一致）+ AssetNotFound 改 `Button asChild + Link` 修 DOM 嵌套。
**实施**：M2 视觉收尾 PR Task 7 + follow-up。

### 6. M2 · SectionHeading 抽双组件

**问题**：simplify §W 登记的 5 处 section caption className 串复制。
**决议**：拆 `<SectionTitle>`（详情阅读区 lg medium）+ `<SectionCaption>`（表单/元信息 uppercase border-b）双组件。本 PR 只替换 5 处 caption；reading-mode 形态保持现状。type-detail-page "元信息" caption 因继承 SectionCaption base 的 `border-b pb-1.5`，与其他 caption 视觉统一（原 inline 缺 border 是历史选择）。
**实施**：M2 视觉收尾 PR Task 4 + Task 6。

### 7. 未做项（登记到 simplify §7）

- M1 TypesTable 未接 Motion 三时刻 — M3 决议
- M3 页面 H1 字号三档无 type scale token — M3 看板/导出加 h1 时一并约定
- M4 attachment-grid `transition-shadow` 配错 prop 名 — M3 触碰附件 grid 时顺手

---

## 实施期纠偏（M3a，2026-05-04）

frontend-design skill 对 M3a PR-2 改动做合并前对照（spec [§5.11](../../docs/superpowers/specs/2026-05-03-m3a-state-machine-design.md)）。本里程碑新增 override：

### 1. 新增 `--status-disposed` / `--status-disposed-fg` OKLCH token pair

DISPOSED（已处置）状态的 token，完全去色相纯灰（chroma=0），与 RETIRED（保留微弱蓝色相）区分。light/dark 两套 + `@theme inline` 映射。落地于 commit `450c982`。

### 2. Toggle chip 模式（filter 区使用 status token 染色的 Toggle，非普通 checkbox）

列表 filter 区 "已退役" / "已处置" 两个独立 Toggle chip，按 status token 染色（off muted / on `bg-status-X/15` + `text-status-X-fg` + `border-status-X/30`）。视觉与 status pill 体系延续。URL 持久化（`?show_retired=true&show_disposed=true`）。落地于 commit `3defbb2`。

### 3. DisposeAlertDialog 二次确认形态

DISPOSE 终态不可逆，dialog 内输入"处置"二字解锁主按钮（参考 `delete-asset-alert.tsx` pattern）。destructive 红色按钮 + Trash2 icon。落地于 commit `db4ff24`。

### 4. timeline 10 kind icon × token 配置表

`transition-timeline.tsx` 的 KIND_META 表显式列 10 kind 对应的 lucide icon + status token + 文案：CHECKOUT_INTERNAL（ArrowRightFromLine）/ CHECKOUT_EXTERNAL（Send）走 status-in-use；RETURN（Undo2）/ RECOVER_FROM_MAINTENANCE（CheckCircle2）/ REINSTATE（Sun）走 status-idle；SEND_TO_MAINTENANCE（Wrench）走 status-maintenance；RETIRE（Moon）走 status-retired；DISPOSE（Trash2）走 status-disposed；RELOCATE（MapPin）/ TRANSFER_HOLDER（UserCog）走 muted 中性。沿用 M2c-2 卡片堆叠形态，§14.8 高级视觉留 M3d。落地于 commit `c7e6195`。

### 5. RETIRED Icon 从 `MinusCircle` 改 `Moon`

"休眠待复活"语义，与 RETIRE transition kind 在 timeline 的 icon 一致；M2c-1 旧 MinusCircle 弃用。落地于 commit `4f2500a`。

### 6. 派发/出借拆为两个主按钮（修订 spec §5.4 决议）

**原决议**：spec §5.4 把 CHECKOUT_INTERNAL / CHECKOUT_EXTERNAL 合一为 `DISPATCH_GROUP`，单个"派发"主按钮 + dialog 内 ToggleGroup 选类型。

**修订原因**：M3a 验收发现 dialog 内 toggle discoverability 不足——主按钮就叫"派发"，用户不点开 dialog 看不到出借入口存在。

**新决议**：IDLE 状态详情页主按钮区**并列两个按钮**："派发" + "出借"。CheckoutDialog **共用一个组件 + `kind` prop**，按 kind 切换 icon（ArrowRightFromLine vs Send）/ chip 文案（派发 vs 出借）/ 字段 label（派发给 vs 出借给）/ 描述（派发给团队成员 vs 出借给外部人员）/ 按钮文案 / toast。

**视觉决议（二次修订）**：所有 transition 主按钮（派发/出借/归还/维修完成/重新启用）等权用 `default` variant，颜色一致——transition 是同一类操作，不应人为区分主次。**编辑**作为导航操作（非 transition）放主按钮区但用 `outline` variant（视觉分层不抢 transition 主路径）；DISPOSED 全只读时隐藏。⋯ 菜单只承载次要 transition（送修/退役/relocate/transfer-holder/dispose）+ 删除。

`available-transitions.ts`：`PRIMARY_ACTION` rename 为 `PRIMARY_ACTIONS`，类型 `Record<AssetStatus, PrimaryAction[]>`（数组），删除 `DISPATCH_GROUP` 字面量。

列表行尾菜单同步：单"派发"项扩为"派发 / 出借"两项（`onCheckout(row, kind)` 签名）。

落地于 M3a 后续 fix commit。

### Pre-Delivery Checklist（M3a PR-2 验证）

- [x] No emojis as icons（全 Lucide SVG）
- [x] cursor-pointer on clickable elements
- [x] Hover transitions smooth 150-300ms（`transition-colors`，无 `transform: scale`）
- [x] Light mode text contrast 4.5:1
- [x] Focus states visible for keyboard
- [x] `prefers-reduced-motion` respected（沿用 M2c-1 globals.css）
- [x] Responsive 1024+

### 红线扫描结果

`grep -rnE 'scale-|animate-spin|animate-pulse|backdrop-blur|bg-gradient-to'` 在 PR-2 新增/修改文件内：**1 命中**（`frontend/src/components/ui/skeleton.tsx:7` 的 `animate-pulse`，shadcn skeleton 标准、早于 M3a 引入）。新文件 0 命中。

### Playwright MCP 烟测（6 场景，2026-05-04）

| # | 场景 | 结果 | 截图 |
|---|------|------|------|
| 1 | Happy path 派发→归还→送修→维修完成→退役→重新启用 | ✅ 6 行 timeline 各 kind icon + token 染色 | `smoke-scenario1-happy-path.png` |
| 2 | DISPOSE 输入"处置"二次确认 + DISPOSED 全只读 | ✅ 按钮 disabled→输入解锁；菜单仅剩"删除" | `smoke-scenario2-disposed-readonly.png` |
| 3 | 列表 Toggle 显隐 RETIRED/DISPOSED + URL 持久化 | ✅ `?show_retired=true&show_disposed=true` 同步 | `smoke-scenario3-toggle-show-all.png` |
| 4 | RELOCATE / TRANSFER_HOLDER 走 ⋯ 菜单（IDLE） | ✅ ⋯ 菜单可见 + Relocate dialog 可用 | （内嵌场景 1） |
| 5 | timeline 10 kind 视觉差异化 | ✅ 9 kind 实跑过；CHECKOUT_EXTERNAL/TRANSFER_HOLDER 同源代码路径 | （场景 1+2 timeline） |
| 6 | dark mode + light mode + status-disposed token | ✅ 双主题 chip 视觉清晰区分 | `smoke-scenario6-dark-mode-list.png` |

### 烟测发现 followup（非 blocker）

- 列表 Toggle pressed 视觉态较弱（chip 在 on 时与 off 视觉差异不够明显）—— spec §5.10 review 时考虑加重 `data-[state=on]` 边框

---

## 排版 type scale（M3d 引入）

页面 H1 字号按页面分类二档：

| 页面分类 | utility | 用例 |
|---|---|---|
| 列表 / 配置页 | `text-xl font-semibold` | `/types`（类型列表） |
| 详情页 | `text-2xl font-semibold` | `/assets/:id` / `/types/:id` |
| 看板（hero）| 不纳入此约定 | `/dashboard` 用 `text-3xl font-medium tracking-tight` 独立形态 |

新加页面前按归类挑选；偏离需在本表加行说明。

---

## 实施期纠偏（M4，2026-05-20）

frontend-design skill 合并前闸门由控制器直接判定（M4 改动严格按 MASTER token + 公共组件复用，无创新视觉决策——所有视觉决策点 Phase 7.2 / 7.3 控制器提前下了方案）。

### 1. Dashboard atmosphere radial gradient token 实际落地

`--dashboard-bg-radial-from/to` token 早在前期里程碑已定义 light/dark 两套，但 dashboard route 容器 JSX 之前仅用 inline `style={{ backgroundImage: "radial-gradient(circle at 50% 20%, ...)" }}`，未消费 token。本里程碑改为 Tailwind class `bg-[radial-gradient(50%_60%_at_50%_20%,var(--dashboard-bg-radial-from),var(--dashboard-bg-radial-to))]`，gradient 参数从 `circle at 50% 20%` 矫正为 `50% 60% at 50% 20%`，与原 token 注释「顶部 50% 20%」对齐。落地于 commit `f8515e0`。消除 dashboard 卡片 `bg-card` 与全局 `bg-background` 的色块割裂（spec M4-B 修复点 #1）。

### 2. Toggle chip pressed 边框透明度 /30 → /60

M3a 实施期纠偏 §2 引入的 Toggle chip 模式（off muted / on `bg-status-X/15` + `text-status-X-fg` + `border-status-X/30`）实测发现 pressed 视觉态较弱（chip on 时与 off 视觉差异不够第一眼可见，spec §5.10 列入 followup）。本里程碑修订：**列表 + dashboard 两端 Toggle chip 的 `border-status-X/30` 全部改为 `border-status-X/60`**。其他三态 className 不动（`bg-status-X/15` + `text-status-X-fg` 视觉权重保持，避免与 status pill 抢戏）。落地于 commit `8f9d982`。控制器决策方案 A（边框加深 1 级，不加 ring）。

### 3. Dashboard chart 空态 thin wrapper 模式

dashboard 4 个 chart 卡片（闲置 Top / 类型分布 / 状态分布 / 保管人分布）各自空态文案语义差异大，强塞 `<EmptyState title description>` 通用结构丢语义。本里程碑在 `frontend/src/features/dashboard/empty-states/` 新增 4 个 thin wrapper（`IdleEmpty` / `TypeEmpty` / `StatusEmpty` / `HolderEmpty`），各自 hardcoded title/description/icon，内部仍用公共 `EmptyCard`（`EmptyState` 的 chart 变体壳）。**不给 `<EmptyState>` 加 `variant` prop**（避免污染 22 处调用方），**不 inline 实现**（违反公共组件复用）。落地于 commit `2be7c1e`。控制器决策方案 (b)。

### 4. Dashboard filter toggle 文案统一

dashboard `dashboard-header.tsx` 的 "已退役 / 已注销" 与列表 `assets-filters.tsx` 的 "显示退役 / 显示注销" 文案不一致（v2.0 followup-allocation 衍生 minor）。本里程碑统一为 "显示退役 / 显示注销"（与 STATUS_META label 配套语义更清晰）。落地于 commit `f8515e0`。

### 5. CheckoutDialog / ReturnDialog 抽 useFormDialog hook 收敛样板

两 dialog 内 `useForm + zodResolver + onSubmit (含 try/setError('root')) + handleOpenChange (含 mutation 进行中防关闭)` 完全相同 ~30 行样板抽到 `useFormDialog<T>` 泛型 hook。各 dialog 体净减 ~30 行，仅保留字段定义 + mutate mapping + 描述文字。外部行为零变化（现有 dialog test 全绿）。落地于 commit `3a4f324`。

### Pre-Delivery Checklist（M4 PR 验证）

- [x] No emojis as icons（全 Lucide SVG；本 PR 新引入图标仅 dashboard empty wrapper 4 个）
- [x] cursor-pointer on clickable elements（shadcn Button / Toggle 默认；M4-E 列表 type/status 列 header 改为可点击排序走 TanStack Table 默认 cursor 处理）
- [x] Hover transitions smooth 150-300ms（仅 `transition-colors` 类 + 边框透明度变化；无 `transform: scale`）
- [x] Light mode text contrast 4.5:1（status 色 token 沿用 MASTER 锁定值；Phase 7.2 verified BROKEN token 未被改）
- [x] Focus states visible for keyboard（globals.css `*:focus-visible` 兜底；M4-E sortable header 走 shadcn Table 默认）
- [x] `prefers-reduced-motion` respected（沿用 M2c-1 globals.css 媒体查询；本 PR 无硬编码新动画）
- [x] Responsive 1024+（dashboard 改 `grid-cols-12` + chart 卡片 `col-span-6`；< 1024 自动换行 shadcn responsive grid 默认）

### 红线扫描结果

`grep -rnE 'scale-|animate-spin|backdrop-blur|bg-gradient-to'` 在 M4 改动面（dashboard / list / detail / components）：**0 命中**（shadcn `skeleton.tsx:7` `animate-pulse` 是历史例外，本 PR 未改）。

### Playwright MCP 烟测

本 PR 视觉烟测由 e2e CI 覆盖（新加 `list-sort-by-type-status` spec + 现有 11 spec），跳过 Playwright MCP 手测。Phase 2 IdleTopBarChart Y 轴长名截断决策点未触发（待生产数据后再 followup 评估）。

## 实施期纠偏（UI 一致性 batch PR-2，2026-05-27）

收口「前端视觉/结构一致性 batch」（spec `docs/superpowers/specs/2026-05-26-ui-consistency-batch-design.md` 决策 1/4/5/6 + E）。纯前端，无 schema 改动。本 PR squash 合并，下列各项落地于同一 squash commit（非逐条独立 SHA）。

### 1. D1 · 撤销 Dashboard Atmosphere（radial gradient）→ 平背景

**反向纠偏 M4 实施期纠偏 §1。** M4 §1 把 dashboard `<main>` 容器改用 `bg-[radial-gradient(50%_60%_at_50%_20%,var(--dashboard-bg-radial-from),var(--dashboard-bg-radial-to))]` 消费 atmosphere token。实测浅色模式下该 radial（中心 `oklch(0.985)` 中性灰 → 边缘纯白）与全站其它页面的平 `bg-background`（带蓝调 off-white）产生**可见色差**——看板成了带色块的非均匀面，与列表/类型页割裂。本 PR（决策 4）改回平 `bg-background`，与全站一致。`--dashboard-bg-radial-from/to` token 暂留为 dead（无引用，删除放后续清理，本 PR 不强删以缩小改动面）。**MASTER「Dashboard Atmosphere」override 自此作废**：dashboard 背景规则回归 MASTER baseline（平 `bg-background`）。

### 2. D2 · 看板右列去强制等高，改自然堆叠

**修订 M4 §Responsive 的 dashboard grid。** 右列原 `grid grid-rows-3 ... min-h-[640px]` 把右列强制切 3 等高行（各 ~213px），但行内卡片（`<section>`，无 `h-full`）按内容高度浮在行顶 → 下方死空间 = 大间距。决策 5：外层 grid 去 `min-h-[640px]` 加 `items-start`（左右两列各自顶对齐、按内容高度不互相拉伸），右列 `grid grid-rows-3` → `flex flex-col gap-6`（三卡按内容自然堆叠）。`HolderLeaderboard` 已自带 `HolderEmpty` 空态，无需新增。加载骨架 `skeleton.tsx` 的 `DashboardSkeleton` 同步对齐（去 `min-h-[640px]` 加 `items-start`、内层 `grid grid-rows-3` → `flex flex-col`），消除 loading→data 的布局抖动（终审 M1 发现，同 D2 逻辑补齐）。

### 3. §S · toggle 统一为共享 StatusFilterToggle（语义图标）

**承接 M4 §2（边框 /60）+ §4（文案统一），收掉两套实现。** 列表 `assets-filters.tsx`（shadcn Toggle + 语义图标 Moon/Archive）与 dashboard `dashboard-header.tsx`（自定义 `TogglePill` + **圆点** 指示符）此前是两套独立实现。决策 6：抽 `frontend/src/components/status/status-filter-toggle.tsx` 共享组件（基于 shadcn `Toggle`，props `pressed/onPressedChange/icon/label/status`，导出判别类型 `StatusKey`），**指示符统一为语义 Lucide 图标**（Moon=退役 / Archive=注销，与 timeline `RETIRE=Moon` 一致），染色 token 沿用 M4 §2 锁定值（`bg-status-X/15` + `text-status-X-fg` + `border-status-X/60`）。dashboard 删 `TogglePill` + `TogglePillProps`（圆点→图标）。两端 label 统一为「显示退役 / 显示注销」（沿用 M4 §4），列表 toggle 可见文本由共享组件 `aria-label === 可见文本` 同源，消除原 `aria-label="显示退役资产"` + 可见文本「显示退役」的分裂。

### 4. §W-列表 · page-header 规范统一

决策 1：统一「列表页头」=`<h1 text-xl font-semibold>` 标题 + 计数副标题 `<p text-sm text-muted-foreground>` + 右侧主操作，标题文案**对齐 nav 标签**。落地：`types-page.tsx` 标题「类型管理」→「类型」；`routes/index.tsx` 资产列表**补 page-header**（原无标题）——加标题「资产」+ 计数「共 N 件」（筛选后 `query.data.length`），登记按钮上移到标题行，filters + 列显隐/导出留在下方一行。两页标题行 className 对齐（`flex items-end justify-between gap-3`）。顺手修复 `index.tsx` 登记按钮 `<Link><Button>`（`<a>` 嵌套 `<button>` 的非法可交互元素嵌套）→ `<Button asChild><Link>`，与 sibling `types-page.tsx` 既有的 shadcn 范式一致。三页（资产/类型/看板）page-header 风格自此统一。

### 5. E（逾期角标加载闪动）· 不做

决策文档列 E 为可选。评估结论：现状（`useOverdueForOpenCheckout` 在 transitions 加载期返回 null → 角标加载完才渲染、不渲染占位）已是**无布局跳动的最稳妥形态**；加等宽占位反而可能引入视觉噪音，ROI 低。维持现状，E 不做。

### Pre-Delivery Checklist（PR-2 验证）

- [x] No emojis as icons（toggle 指示符由圆点 div 改为语义 Lucide Moon/Archive；全 SVG）
- [x] cursor-pointer on clickable elements（shadcn Toggle / Button 默认）
- [x] Hover transitions smooth 150-300ms（StatusFilterToggle `transition-colors duration-200`；D1/D2 纯布局类无新动画）
- [x] Light mode text contrast 4.5:1（status 色 token 沿用 MASTER 锁定值未改；D1 改回 `bg-background` 提升对比一致性）
- [x] Focus states visible for keyboard（shadcn Toggle / Button focus-visible 默认 + globals.css 兜底）
- [x] `prefers-reduced-motion` respected（沿用 globals.css 媒体查询；本 PR 无硬编码新动画）
- [x] Responsive 1024+（dashboard 仍 `grid-cols-12` + `col-span-6`；右列改 `flex flex-col` 不影响 < 1024 换行）

### 红线扫描结果

`grep -rnE 'scale-|animate-spin|backdrop-blur|bg-gradient-to|radial-gradient'` 在 `frontend/src` 全树：**0 命中**（D1 去 radial 后 dashboard 不再有 `radial-gradient`；shadcn `skeleton.tsx` `animate-pulse` 是历史例外，不在本 pattern 内、本 PR 未改）。后端无改动，未跑 `gen:api`。

### Playwright MCP 烟测（浅色模式，2026-05-27）

作者主用浅色，本批问题（D1 色差）只在浅色明显，故**先在浅色模式**走查（`<html>` 无 `dark` class 即默认浅色）：

- `/dashboard`：背景平整无色差（D1 ✅）；右列三卡（类型分布/状态分布/保管人持有）自然堆叠、间距一致、无死空间（D2 ✅）；toggle 为图标 pill（Moon/Archive，§S ✅）。
- `/`：页头标题「资产」+「共 5 件」+ 登记资产按钮上移到标题行；下方 filters 行的「显示退役/显示注销」为图标 pill（§W + §S ✅）。
- `/types`：标题「类型」（非「类型管理」）+「共 2 个类型」（§W ✅）。
- 三页 page-header 风格一致（标题左 / 主操作右）。

gate 全绿：`tsc -b` clean、`lint` 0 errors（2 个 pre-existing useReactTable warning）、`vitest` 46 files / 197 tests 全通过。
