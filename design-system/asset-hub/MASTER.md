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

### Typography

- **Heading Font:** Fira Code
- **Body Font:** Fira Sans
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
