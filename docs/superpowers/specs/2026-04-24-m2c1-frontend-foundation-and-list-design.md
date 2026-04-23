# M2c-1 · 前端地基 + 资产列表页 设计文档

- **日期**：2026-04-24
- **里程碑**：M2c 第 1 子项（地基 + 列表）
- **状态**：初稿，待实施
- **作者**：conghaoyangbobby@gmail.com（与 Claude 协同 brainstorm）
- **承接**：[`2026-04-15-asset-hub-design.md`](./2026-04-15-asset-hub-design.md) §7 / §11

## 0. 导读

本文档是 **M2c 子里程碑拆分后的第 1 份 spec**。M2c 整体（spec §7 Web GUI）拆为三步，每步各有自己的 spec + plan：

| 子里程碑 | 范围 | spec |
| --- | --- | --- |
| **M2c-1 · 地基 + 列表**（本文） | 前端工具链、数据层、主题、布局壳、资产列表页 | 本文 |
| **M2c-2 · 详情 + 流转** | 详情页 + 派发/归还对话框 + 流转时间线 + 附件查看 | 未写 |
| **M2c-3 · 表单 + 附件上传** | 登记/编辑表单（动态 `custom_fields`） + 附件上传 UI | 未写 |

M3（看板 + 导出 + 类型管理 UI）、M4（审美打磨 + 命令面板 + 响应式）均在 M2c 完结之后再动。

## 1. 目标与非目标

### 1.1 目标

把后续所有 Web 页面要共用的**地基**一次性铺好，同时交付第一个端到端可用的页面——资产列表。

- 前端工具链：`openapi-typescript`（生成）+ `openapi-fetch`（运行时）+ `@tanstack/react-query`（数据层）+ `sonner`（toast）+ TanStack Router typed search params
- 设计系统 baseline：以 `ui-ux-pro-max` 生成物为准、`frontend-design` 审美纠偏
- 应用壳：`AppLayout`（header + toast + theme toggle），light-first 双模主题
- 资产列表页 `/`：表格 + 筛选 + 排序 + 分页 + 列显隐 + URL-synced state + 空/错/载态
- 公共组件：`StatusBadge / EmptyState / ErrorState / SkeletonRow / ThemeToggle / ErrorBoundary`

### 1.2 非目标（明确推走）

| 非目标 | 去处 |
| --- | --- |
| 资产详情页 `/assets/:id` | M2c-2 |
| 派发/归还对话框、流转时间线 | M2c-2 |
| 附件查看（lightbox、缩略图） | M2c-2 |
| 登记/编辑表单（动态 `custom_fields`） | M2c-3 |
| 附件上传 UI | M2c-3 |
| 批量选择 + 批量操作 | M3 |
| 导出按钮（`GET /api/export` 尚未实现） | M3 |
| 看板 `/dashboard`、类型管理 `/types` | M3 |
| 命令面板（⌘K）、响应式、微动效打磨 | M4 |
| i18n 脚手架 | 直接硬编码中文，未来再议 |
| 前端单测 / 组件测试 | M2c-3 引入 Vitest，本里程碑靠 build+lint+人工烟测+`frontend-design` review |
| 后端列表端点的 sort / pagination 支持 | 仅在资产量突破 2000 时再评估 |

## 2. 关键决策（已定）

每条决策的源头在 brainstorm 会话中逐个对齐，此处定型。后续若有翻面请在本节留 changelog。

| ID | 决策 | 选项 | 理由 |
| --- | --- | --- | --- |
| D1 | M2c 范围颗粒度 | 拆成 M2c-1 / M2c-2 / M2c-3 | 单一 spec+plan 会过大（参考 M2b plan 1867 行），拆分后每个子 plan 可控 |
| D2 | API 客户端 | `openapi-fetch` + `@tanstack/react-query` 手工接线 | 依赖最少、可控；TanStack Query 是行业事实标准；hey-api 的自动生成对我们规模过重 |
| D3 | 列表交互模型 | 全客户端 sort / paginate + URL-synced filters | 后端零改动；v1 资产量级 <500；URL 可分享 / Agent 可构造；TanStack Table 切 server-side 代价低 |
| D4 | 主题模式 | 双模支持，**默认 light**，提供 Light / Dark / System 三态切换 | 日常高亮办公室、白天长时间使用、中文大段正文浅色阅读疲劳低；dark 仅作备选能力 |
| D5 | 列表页 v1 范围（多选） | URL-sync、列显隐 localStorage、行点击跳详情+⋯ 快速动作占位、Toast、统一空/错/载态、全局 ErrorBoundary，**不做**批量/导出/i18n/命令面板 | 与 D1 一致：把"地基 + 可用列表"做透、不越权 M2c-2/3/M3/M4 |
| D6 | 设计 baseline 生成 | `ui-ux-pro-max --design-system --persist` 在 brainstorm 阶段跑完、产物纳入 git；`frontend-design` 作为实施期 review 闸门 | 让 spec 的色/字/效建立在真实数据上，关键词现在调成本最低；`frontend-design` 的"避免 AI 模板脸"在实施期发挥最大价值 |
| D7 | 主品牌字 | UI 可见处统一显示"**小组资产管理工具**"；技术代号 `asset-hub` 仅用于 `<title>`、`<html lang>` | 与设计文档 §1 口径一致（"小组内部使用的资产管理工具"） |
| D8 | 审美方向（frontend-design 承诺） | **工业实用主义极简 + 键盘驱动的密度感**；Fira Code/Sans + 中文 PingFang SC；3 个 Motion 时刻、其余禁动效；禁 glassmorphism / 多层阴影 / shadcn 默认 variant | 详见 §3.5；frontend-design skill 提前到 spec 阶段介入（§3.4 ①），让审美决策可追溯、可审计，避免实施期才发现结构性偏差 |

## 3. 设计系统 baseline

### 3.1 生成物（纳管 git）

来自 `ui-ux-pro-max` skill，已在 brainstorm 阶段执行：

```bash
# MASTER（锚点产品类别：Analytics Dashboard）
python .claude/skills/ui-ux-pro-max/scripts/search.py \
  "internal admin dashboard panel data dense professional" \
  --design-system --persist -p "asset-hub" -f markdown

# 列表页 override
python .claude/skills/ui-ux-pro-max/scripts/search.py \
  "admin inventory crud drill-down data grid list" \
  --design-system --persist -p "asset-hub" --page "assets-list" -f markdown
```

产物路径：
- `design-system/asset-hub/MASTER.md` —— 全局权威 tokens
- `design-system/asset-hub/pages/assets-list.md` —— 列表页覆盖

### 3.2 提取的权威 tokens（来自 MASTER）

| 项 | 值 | 用途 |
| --- | --- | --- |
| Pattern | Data-Dense + Drill-Down | 列表→详情→操作的导览逻辑 |
| Style | Data-Dense Dashboard（WCAG AA） | 最小 padding、网格布局、信息密度优先 |
| Primary | `#1E40AF`（navy-800） | 主按钮、链接、聚焦环 |
| Secondary | `#3B82F6`（blue-500） | 辅助强调 |
| CTA / Accent | `#F59E0B`（amber-500） | 关键动作、重要标注 |
| Background（light） | `#F8FAFC`（slate-50） | light 模式底色 |
| Text（light） | `#1E3A8A`（navy-900） | light 主文本 |
| Heading 字体 | Fira Code（Variable 优先） | 标题、`asset_code` 等编号字段 |
| Body 字体 | Fira Sans（Variable 优先） | 正文；中文 fallback：`"PingFang SC", "Microsoft YaHei UI", system-ui` |
| 反模式（anti-patterns） | Ornate design、No filtering | 全局红线 |
| 关键效果 | Hover tooltips、row highlighting、smooth filter animations | 本里程碑必做：row highlighting + filter 平滑过渡 |

**Dark mode 变量**由 light 值**手工配对**（不由 skill 给），策略在 §6.2 展开。

### 3.3 列表页 override 的取舍（来自 pages/assets-list.md）

**采纳**：

- Max Width：`1400px`（或 full-width）
- 布局：12 列栅格，Content Density: High
- 反模式补充：`Single row actions only`（佐证我们保留"行点击跳详情 + 行尾 ⋯ 菜单"双入口，而不是把所有操作都挤在行尾）
- Effects：Drill-down expand animations、smooth detail reveal（为 M2c-2 留白，本里程碑只做"行高亮"和"筛选过渡"）

**忽略（noise，由 frontend-design review 兜底）**：

- "Project Grid Masonry" —— 作品集模板窜味
- "Hero (Name/Role)" —— 个人主页模板窜味
- "Contact CTA" —— 落地页模板窜味
- "Compress and lazy load 3D models"、"50MB textures"、"Auto-play video loops" —— 资产管理页与之无关
- "Multi-select and bulk edit" —— 与 D5 冲突（本里程碑不做，推到 M3）

### 3.4 `frontend-design` skill 的四阶段介入（不止于实施期）

将 skill 的 "commit to a BOLD aesthetic direction" 原则**前移到 spec 阶段**，避免等到实施期做事后补救。四个介入节点：

| # | 阶段 | 职责 |
| --- | --- | --- |
| ① | **Spec 阶段（本次）** | 把审美方向、字体合规、Motion 战略、Depth 战略、反通用字体红线**写入 §3.5**，让决策可追溯可审计 |
| ② | **Plan 撰写（writing-plans）** | 每个 UI-ish Task **显式引用** §3.5 的某条约束作为设计依据，禁止"implement X"式模糊任务 |
| ③ | **Plan 评审（写完 plan 后）** | 以 frontend-design 原则扫 plan：是否有隐性的"shadcn 默认即可"、是否漏了 §3.5 承诺的 3 个 Motion 时刻、是否有通用字体渗入 |
| ④ | **实施期 3 个闸门**（保留原方案） | `globals.css` 完成后 / `AssetListPage` 骨架可跑后 / M2c-1 合并前——在真实代码上做最终审美与反模式审查；Pre-Delivery Checklist（见 MASTER）逐项勾 |

Review 发现的偏差**回写** `design-system/asset-hub/MASTER.md` 或 page override 作为"实战纠偏备注"，形成闭环。

### 3.5 审美纲领（frontend-design 的 spec 级承诺）

本节是 frontend-design skill 在 spec 阶段的**强制输出**：每个 UI 决策都必须可追溯到以下条目。违反任何一条须在 PR 描述中显式说明理由。

#### 3.5.1 审美方向（Tone）

**工业实用主义极简（industrial utilitarian minimalism）**。

为什么是这个而不是别的：
- 本产品是"单用户 + AI Agent"的**操作台**，不是给陌生人看的产品页，不是 marketing，不需要讨好眼球
- 信息密度是硬需求（spec §3 / MASTER "Content Density: High"）；"refined minimalism" 和 "industrial utilitarian" 的交集正好服务密度
- 不走 "brutalist raw" 或 "maximalist chaos"——它们会让每日使用疲劳；不走 "playful" / "luxury"——调性不符

**具体表现**：
- 几何克制：直角为主，`--radius` 不超过 6px；大圆角禁入
- 装饰零容忍：禁用渐变背景、光晕、光点、emoji、无来由的阴影
- 留白是构造工具、不是豪华符号：行距按 1.5-1.6、段落留白按 24/32px 节奏，但**不**用 64px+ 的"呼吸空间"
- 信息层级通过字重 / 色温 / 字号差异建立，**不**靠 container shadow 或 card 边框层堆叠

#### 3.5.2 差异点（Differentiation）—— "The One Memorable Thing"

**键盘驱动的密度感（keyboard-first density）**：一个懂行的人看到本工具的第一反应应当是——"这东西是为持续操作设计的，像 IDE 而不像后台"。

落实到可审计的具体特征：
- **可见的 focus ring**：每个交互元素的 `:focus-visible` 状态都是"显眼的方块框"，不是 shadcn 默认那种淡蓝描边（细节待 §3.5.5 motion 与此协调）
- **等宽数字**：所有表格数字列启用 `font-feature-settings: "tnum"`，列宽不因数字抖动
- **编号字段等宽字体**：`asset_code / serial_number` 切 Fira Code，其余保持 Fira Sans；这种"局部字型切换"本身就是差异化
- **hover/selected 状态的色温差异 > 亮度差异**：让长时间盯表时眼不疲劳

#### 3.5.3 字体合规（反"AI 通用字体"审计）

| 允许 / 禁止 | 字体 | 备注 |
| --- | --- | --- |
| **✓ 允许（主用）** | Fira Code（heading + mono） | 技术感、非通用、与 MASTER 一致 |
| **✓ 允许（主用）** | Fira Sans（body） | 同上 |
| **✓ 允许（中文 fallback）** | PingFang SC、Microsoft YaHei UI | 有意选择而非 `system-ui` 兜底 |
| **✗ 禁止** | Inter / Roboto / Arial / Helvetica / Open Sans / SF Pro / system-ui 作为主字体 | frontend-design skill 明令反通用字体 |
| **✗ 禁止** | Space Grotesk / Geist / Satoshi 作为主字体 | 虽非 Arial 但已是 "AI 生成标配"——同样反通用 |

> **字体包版本说明（2026-04-24 实施期纠正）**：Fira Sans 在 Google Fonts 上**没有 variable font 发布**（`@fontsource-variable/fira-sans` 在 npm 上 404）。为保持两种字体包约定一致，本里程碑统一采用 `@fontsource/*`（静态字体包），`@fontsource-variable/fira-code` 虽存在但**不使用**。bundle 相比理论最优 variable 方案略大（~100KB 量级），放 M4 UI 打磨期再评估是否分字体混用。相应地，globals.css 的 `font-family` 字面量统一写作 `"Fira Sans"` / `"Fira Code"`（去掉 `Variable` 后缀）。

**审计点**：`globals.css` 的 `@theme` 段不得出现 Inter/Roboto/system-ui；实施期第一条 Task 必须替换掉现有 `@fontsource-variable/geist`。

#### 3.5.4 配色深化（超出 MASTER）

MASTER 给的是 token，但 **"如何用"** 是 frontend-design 的辖区：

- **Dominant + accent** 结构硬约束：Primary（navy）占 UI 主色约 70%、text 与 dividers 灰度占 25%、CTA（amber）仅用于"真正的关键动作"（例如"派发""登记"），占比 <5%
- **禁止**：紫色渐变、多 accent 并用、背景渐变铺底
- **Dark 模式**：不是把 light 反转；要**独立调**——dark 下 Primary 亮度要上提、饱和度下压（避免刺眼"电子蓝"）；amber 在 dark 下要降亮度以避免"屏保广告感"
- 状态语义色（§6.2 4 个 `--status-*` 变量）必须视觉上**不与 Primary/CTA 撞脸**——实施期定值时先打印所有色块对比图，肉眼验一次

#### 3.5.5 Motion 战略（3 个高影响力时刻，其余一律禁用）

遵循 skill 的 "one well-orchestrated page load with staggered reveals creates more delight than scattered micro-interactions"。

**允许且必做**的三个时刻：

1. **首屏表格 stagger reveal**：首次加载（不是每次切筛选！）前 20 行以 `animation-delay` 依次淡入 + 下移 4px，每行间隔 15-25ms，总时长 ≤400ms
2. **筛选变更时表格淡切**：切 filter / 排序 / 翻页时，`<tbody>` 整体 `opacity 0 → 1` + `translateY 4px → 0`，120-160ms，`ease-out`
3. **State pill 色变**：`StatusBadge` 在状态切换时用 `transition-colors` 150ms（只换色，不换尺寸）

**全局禁用**：
- 按钮 hover 放大 / 缩小（任何 `transform: scale()`）
- 背景动画（渐变漂移、粒子、光圈）
- 页面进场 fade / slide（路由切换直接显示）
- 任何 >400ms 的过渡
- `animate-spin`（加载就用骨架行，不用 spinner）

**尊重 `prefers-reduced-motion`**：该偏好打开时，3 个时刻全部降级为无动画的瞬时切换。

#### 3.5.6 Depth 战略（反 solid-color block）

skill 原话：`"Create atmosphere and depth rather than defaulting to solid colors"`。但本产品气质要求克制。取中：

- **允许的 depth 语法**：
  - 1px hairline dividers（`--border` token，不用 shadow 伪装分隔）
  - Light 模式 card 用极浅 inset shadow（`0 1px 0 0 rgba(0,0,0,0.02) inset`）暗示层次，**不**用 drop shadow
  - Table `hover` 行用背景色温差（比周围略暖或略冷），**不**用 box-shadow 外圈
- **禁止**：
  - 任何 `blur(Npx)` 背景（glassmorphism）——和工业调性冲突
  - 多层阴影叠加（"elevation 3/4/5"这种 Material Design 派头）
  - 纯色方块 + 无边框 card 堆叠（AI 模板脸的典型症状）

#### 3.5.7 shadcn 组件定制红线

shadcn 生态是双刃剑：不改会长成"AI 模板脸"；要改就必须有纪律。

- **每个首次 `pnpm dlx shadcn@latest add <x>` 进来的组件**必须在同一个 PR 里完成 variant 审查与色值替换——**禁止**留下未改的默认 variant
- Button 的 `default / outline / ghost / destructive` 都要按 §3.5.4 重着色
- Input / Select 的 focus ring 要按 §3.5.2 "显眼方块框"重调
- Badge 的 `variant` 与 `StatusBadge` 形成明确分工——`Badge` 给通用标签（如类型）、`StatusBadge` 给资产状态 4 态（独立组件，不走 `Badge` 的 variant）

---

**spec-level 审美审计结论**：本里程碑 §3.5.1–§3.5.7 已覆盖 frontend-design skill 的 6 类关注点（Tone / Differentiation / Typography / Color / Motion / Depth）；其中 3.5.7 覆盖 shadcn 工具链的反模板防线。实施期的 3 个闸门（§3.4 ④）只负责验证这些承诺是否兑现，不再做方向性决策。

## 4. 架构

### 4.1 承袭自设计文档

CLI 与 Web 共用同一个 FastAPI；Web 通过 HTTP 调 `/api/*`（开发期 Vite 代理 `/api → :8000`）。

```
Web GUI (React/TS) ──HTTP──► FastAPI ──► Service ──► Repository/SQLModel/FS
```

M2c-1 **不修改后端**。

### 4.2 前端目录结构

```
frontend/
├── package.json                    # 修改：加依赖
├── vite.config.ts                  # 修改：确认 /api 代理
├── index.html                      # 修改：<title> + <html lang="zh-CN"> + 防闪烁脚本
├── scripts/
│   └── gen-openapi.ts              # 新：从 http://localhost:8000/openapi.json 生成 schema
└── src/
    ├── main.tsx                    # 修改：挂 QueryClientProvider + ThemeProvider + Router
    ├── routeTree.gen.ts            # 自动生成，别手改
    ├── routes/
    │   ├── __root.tsx              # 修改：AppLayout + Devtools
    │   └── index.tsx               # 修改：AssetListPage 容器（读 search、挂 query、调 features/assets/list）
    ├── api/
    │   ├── generated/
    │   │   └── schema.d.ts         # openapi-typescript 产物（纳管 git）
    │   ├── client.ts               # openapi-fetch 实例
    │   ├── query-client.ts         # QueryClient 实例 + 默认 options
    │   ├── query-keys.ts           # 集中 query key factory
    │   └── hooks/
    │       ├── assets.ts           # useAssetsQuery / useCreateAsset / useUpdateAsset / useDeleteAsset
    │       └── types.ts            # useAssetTypesQuery
    ├── components/
    │   ├── layout/
    │   │   └── app-layout.tsx
    │   ├── theme/
    │   │   ├── theme-provider.tsx
    │   │   └── theme-toggle.tsx
    │   ├── feedback/
    │   │   ├── empty-state.tsx
    │   │   ├── error-state.tsx
    │   │   ├── error-boundary.tsx
    │   │   └── skeleton-row.tsx
    │   ├── status/
    │   │   └── status-badge.tsx
    │   └── ui/                     # shadcn 按需生成
    │       ├── button.tsx / input.tsx / select.tsx / table.tsx
    │       ├── dropdown-menu.tsx / badge.tsx / skeleton.tsx / separator.tsx
    │       ├── tooltip.tsx / sonner.tsx
    ├── features/
    │   └── assets/
    │       ├── list/
    │       │   ├── assets-table.tsx
    │       │   ├── assets-filters.tsx
    │       │   ├── assets-pagination.tsx
    │       │   ├── column-visibility.tsx
    │       │   └── search-schema.ts
    │       └── status-labels.ts    # 4 态的中文名 + CSS token + dot icon
    ├── lib/
    │   ├── utils.ts                # 已有（shadcn cn）
    │   ├── error.ts                # envelope 解析 + toFriendlyMessage
    │   └── debounce.ts             # 轻量 debounce（q 输入用）
    └── styles/
        └── globals.css             # 修改：替换为 MASTER 驱动的 CSS 变量 + 4 态状态色
```

### 4.3 依赖追加（`frontend/package.json`）

```jsonc
"dependencies": {
  "@fontsource/fira-code": "^5.x",   // 新增：§3.5.3（见 §3.5.3 字体包版本说明）
  "@fontsource/fira-sans": "^5.x",   // 新增：§3.5.3
  "@tanstack/react-query": "^5.x",
  "@tanstack/react-table": "^8.x",
  "openapi-fetch": "^0.12.x",
  "sonner": "^1.x",
  "zod": "^3.23.x"
},
"devDependencies": {
  "@tanstack/react-query-devtools": "^5.x",
  "openapi-typescript": "^7.x"
}
```

**移除**：`@fontsource-variable/geist`（§3.5.3 反通用字体审计）。

shadcn 组件按需 `pnpm dlx shadcn@latest add <name>` 生成，最小集：`button / input / select / table / badge / dropdown-menu / skeleton / separator / tooltip / sonner`。**每个首次引入的组件必须在同一 PR 内完成 §3.5.7 的 variant 审查与色值替换**。

## 5. 数据层

### 5.1 契约流水线（openapi-typescript + openapi-fetch）

- 生成时机：后端 API 变更时手动执行 `pnpm --dir frontend gen:api`；产物 `schema.d.ts` **纳管 git**，diff 可见
- 前置：后端 `:8000` 运行中
- 脚本 `frontend/scripts/gen-openapi.ts` 从 `http://localhost:8000/openapi.json` 拉取并写入 `src/api/generated/schema.d.ts`
- `package.json` 加 `"gen:api": "tsx scripts/gen-openapi.ts"`

`src/api/client.ts`：

```ts
import createClient from "openapi-fetch";
import type { paths } from "./generated/schema";

export const http = createClient<paths>({ baseUrl: "/" });
```

**硬约束**：业务代码**只能**从 `src/api/hooks/*` 访问后端；**禁止**在 features/components 里直接 import `openapi-fetch` 或 `paths` 类型。违反即阻合。

### 5.2 TanStack Query 配置

`src/api/query-client.ts`：

```ts
{
  queries: {
    staleTime: 30_000,
    refetchOnWindowFocus: false,
    retry: (n, err) => {
      if (isHttpStatus(err) && err.status >= 400 && err.status < 500) return false;
      return n < 2;
    },
  },
  mutations: {
    onError: (err) => toast.error(toFriendlyMessage(err)),
  },
}
```

`assetTypes` 单独覆盖 `staleTime: Infinity`（类型字典几乎不变，仅在 mutation 后显式 invalidate）。

### 5.3 Query key 约定

`src/api/query-keys.ts`：

```ts
export const qk = {
  assets: {
    all: ["assets"] as const,
    list: (params: AssetListParams) => ["assets", "list", params] as const,
    detail: (id: string) => ["assets", "detail", id] as const,
  },
  assetTypes: {
    all: ["assetTypes"] as const,
    list: () => ["assetTypes", "list"] as const,
  },
} as const;
```

### 5.4 Mutation 失效约定（前瞻表，分里程碑定义）

下表列出全项目 mutation 与其 invalidate 目标，**本里程碑仅定义 `assets.*` CRUD 的 hook（写入但暂无 UI 按钮调用）与 `useAssetTypesQuery` 的只读 hook**；其余 hook 跟随使用它们的 UI 一起在对应里程碑引入。

| 操作 | 失效 key | hook 引入里程碑 |
| --- | --- | --- |
| `createAsset / updateAsset / deleteAsset` | `qk.assets.all` | M2c-1（hook 定义，按钮接线在 M2c-3） |
| `checkout / return` | `qk.assets.all` + `qk.assets.detail(id)` | M2c-2 |
| `uploadAttachment / deleteAttachment` | `qk.assets.detail(id)` | M2c-2（查看删除）/ M2c-3（上传） |
| `createAssetType / updateAssetType` | `qk.assetTypes.all` | M3 |

v1 **不做**乐观更新。

### 5.5 URL typed search params（TanStack Router + Zod）

`src/features/assets/list/search-schema.ts`：

```ts
export const assetsSearchSchema = z.object({
  type: z.string().uuid().optional(),
  status: z.enum(["IN_USE", "IDLE", "MAINTENANCE", "RETIRED"]).optional(),
  holder: z.string().optional(),
  q: z.string().optional(),
  sort: z.string().optional(),      // "asset_code" 升 / "-updated_at" 降
  page: z.coerce.number().int().min(1).default(1),
  pageSize: z.coerce.number().int().min(10).max(200).default(50),
});
export type AssetsSearch = z.infer<typeof assetsSearchSchema>;
```

路由绑定 `validateSearch`；非法参数丢弃或取默认。**筛选变更自动回第 1 页**是硬约定（`useNavigate({ search: prev => ({ ...prev, status: "IDLE", page: 1 }) })`）。

### 5.6 错误映射（HTTP → 中文）

`src/lib/error.ts`：

- `isHttpError(err)` 识别 openapi-fetch 抛出的响应型错误
- `toFriendlyMessage(err)` 映射：
  - `404` → "资产不存在 / 资源已被删除"
  - `409` → `err.detail` 中文化（"编号已被占用" / "该资产正处派发中"）
  - `422` → "数据校验失败：<字段>"
  - `>=500` → "服务端错误，请稍后重试"
  - 网络错误 → "网络请求失败，请检查后端是否运行"
  - 未覆盖回落 → `HTTP ${status}`

Mutation 默认 `onError: toast.error`；Query 错误由 `<ErrorState>` 组件渲染（带 Retry 按钮）。

## 6. 主题（light-first 双模）

### 6.1 `ThemeProvider`（三态）

`src/components/theme/theme-provider.tsx`：

- 状态 `"light" | "dark" | "system"`
- 默认 `"light"`（首次访问无 localStorage 值）
- 持久化 key：`asset-hub.theme`
- `"system"` 模式监听 `prefers-color-scheme` 变化同步切换
- 对外 `useTheme() => { theme, setTheme, resolved: "light" | "dark" }`

通过 `document.documentElement.classList.toggle("dark", resolved === "dark")` 驱动 shadcn `.dark` 变量。

### 6.2 `globals.css` 改造策略

- `:root`（light）以 MASTER 的 `#F8FAFC / #1E40AF / #1E3A8A` 为锚，按 shadcn 变量名填充；**变量名不动**（让所有 shadcn 组件自动跟随），**变量值按 §3.5 纲领重调**
- `--radius` 从当前 `0.625rem`（10px）下调到 **≤0.375rem（6px）**（§3.5.1 几何克制约束）
- `.dark` 变量**手工配对**（不由 skill 给）：参考 shadcn 默认 dark palette 的亮度映射（background 约 `oklch(0.12)`、foreground 约 `oklch(0.96)`），主色相维持 MASTER 的蓝/amber 色相、调亮度与饱和度以适配深底
- 扩展 4 条语义状态变量（light/dark 各一套，对比度 ≥4.5:1）：

```css
--status-in-use:      /* 暖色：绿或 teal 都可，避免与 CTA amber 抢眼 */
--status-idle:        /* 中性灰 / 冷色 */
--status-maintenance: /* 橙/amber 警示色，避免和 CTA 同色 */
--status-retired:     /* 低饱和灰，不抢夺注意 */
```

- 语义色具体值留给实施期配合 MASTER + `frontend-design` review 拍板（参见 §11 "开放决策"）

### 6.3 防首屏闪烁脚本（同步阻塞、极小）

`index.html` 的 `<head>` 末尾（在所有 CSS / React 之前）：

```html
<script>
  (function () {
    var k = "asset-hub.theme";
    var t = localStorage.getItem(k);
    var prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
    var dark = t === "dark" || (t === "system" && prefersDark);
    if (dark) document.documentElement.classList.add("dark");
  })();
</script>
```

**默认 light**：无 localStorage 值时不加 `.dark` class。

### 6.4 `ThemeToggle`

- Header 右上 icon-only 按钮 + dropdown（Lucide `Sun` / `Moon` / `Laptop`）
- a11y：`aria-label="切换主题"`、键盘可达、无 layout shift
- 三态顺序：Light → Dark → System → Light

### 6.5 字体接入（落实 §3.5.3）

- Fira Code / Fira Sans 通过 `@fontsource-variable/*` 装载，**移除现有 `@fontsource-variable/geist`**（Geist 属 "AI 通用字体标配"，§3.5.3 禁用）
- 主字体（英文）：`"Fira Sans"`（静态包，见 §3.5.3 版本说明）
- Fallback 链（中文，有意选择而非 `system-ui` 兜底）：`"PingFang SC", "Microsoft YaHei UI", sans-serif`
- **完整 body font-family**：`"Fira Sans", "PingFang SC", "Microsoft YaHei UI", sans-serif`
- **Heading / mono** 统一：`"Fira Code", ui-monospace, monospace`
- 数字列等宽：`font-feature-settings: "tnum"`，不整列换字体
- 编号字段（`asset_code / serial_number`）局部切 Fira Code

### 6.6 frontend-design review 分工

- **Light 模式**：作为主审美目标（配色、层级、空/错态、阴影）
- **Dark 模式**：只审可用性（对比度 ≥4.5:1、4 态状态色可区分、边框可见）——**不**做独立审美打磨

## 7. UI 组件

### 7.1 `AppLayout`

路径：`src/components/layout/app-layout.tsx`，挂在 `routes/__root.tsx` 的 `component`。

- Header（固定顶部）：
  - 左：品牌字"**小组资产管理工具**"
  - 中：空（预留命令面板）
  - 右：`<ThemeToggle />`
- Main：`<Outlet />`；外层 `max-w-[1400px]` + 水平居中 + 内侧 padding
- Toast：根部挂 `<Toaster />`（sonner）
- Dev 期：`<TanStackRouterDevtools />` + `<ReactQueryDevtools />`（生产构建 tree-shake）

```
┌────────────────────────────────────────────────┐
│  小组资产管理工具                       🌓     │
├────────────────────────────────────────────────┤
│  <Outlet />                                    │
└────────────────────────────────────────────────┘
```

### 7.2 资产列表页

路径：`src/routes/index.tsx`（薄壳）+ `src/features/assets/list/*`（实现）。

组件树：

```
AssetListPage (routes/index.tsx)
│   读 search params（validateSearch）
│   useAssetsQuery(search) + useAssetTypesQuery()
│   三态派发：
│     loading → <SkeletonRow × pageSize>
│     error   → <ErrorState onRetry={refetch} />
│     empty   → <EmptyState />
│     ok      → 下方组件组合
│
├── <AssetsFilters>                  // features/assets/list/assets-filters.tsx
│      <Input q>     防抖 300ms → URL
│      <Select type>   从 useAssetTypesQuery 填充
│      <Select status> 4 态 + "全部"
│      <Input holder>  文本匹配
│      <Button 重置>
│
├── <ColumnVisibility>               // 偏好 key: "asset-hub.list.columns"
│
├── <AssetsTable>                    // TanStack Table 容器
│      列：asset_code(mono) | name | type | status | holder | location | updated_at | ⋯
│      行为：
│        - 整行点击 → navigate(`/assets/:id`) —— 本里程碑落到 404 占位（M2c-2 接）
│        - ⋯ Dropdown 项：编辑 / 派发 / 归还 / 删除 —— **全部 disabled 占位**
│        - 表头点击：三态排序（升 → 降 → 无）写回 URL
│
└── <AssetsPagination>               // page / pageSize 来自 URL；pageSize 可选 20/50/100/200
```

数据量保险：`useAssetsQuery` 响应超过 2000 条时 `console.warn("asset count exceeds client-paginate threshold, consider server-side pagination")`，不影响功能。

### 7.3 公共组件

| 组件 | 路径 | 职责 |
| --- | --- | --- |
| `StatusBadge` | `components/status/status-badge.tsx` | 输入 `AssetStatus` → pill + dot + 中文名；light/dark 各达标 4.5:1 |
| `EmptyState` | `components/feedback/empty-state.tsx` | title + description + optional action；icon/插画由 MASTER 决定 |
| `ErrorState` | `components/feedback/error-state.tsx` | 输入 `error` + `onRetry`；默认消息 `toFriendlyMessage(err)`；Retry 按钮 |
| `SkeletonRow` | `components/feedback/skeleton-row.tsx` | 表格骨架行（列数/行数可配） |
| `ErrorBoundary` | `components/feedback/error-boundary.tsx` | React 层未捕异常兜底；Reload 按钮；dev 展示 stack |
| `ThemeToggle` | `components/theme/theme-toggle.tsx` | 见 §6.4 |
| `ThemeProvider` | `components/theme/theme-provider.tsx` | 见 §6.1 |

状态语义映射集中于 `src/features/assets/status-labels.ts`（**dot 用 Lucide SVG icon，不用 Unicode 字符**，遵守 MASTER `Pre-Delivery Checklist: No emojis as icons` + §3.5.1 装饰零容忍）：

```ts
import { Circle, CircleDot, Wrench, MinusCircle } from "lucide-react";

export const STATUS_META: Record<AssetStatus, {
  label: string;
  tokenVar: string;   // CSS var name，供 StatusBadge 读取
  Icon: LucideIcon;   // SVG 小图标（8-10px），与 label 并排
}> = {
  IN_USE:      { label: "在用",  tokenVar: "--status-in-use",      Icon: CircleDot },
  IDLE:        { label: "闲置",  tokenVar: "--status-idle",        Icon: Circle },
  MAINTENANCE: { label: "维护",  tokenVar: "--status-maintenance", Icon: Wrench },
  RETIRED:     { label: "报废",  tokenVar: "--status-retired",     Icon: MinusCircle },
};
```

## 8. 错误处理（四层）

| 层 | 抓什么 | 处理 |
| --- | --- | --- |
| **Mutation `onError`** | POST/PATCH/DELETE 失败（409/422 为主） | `toast.error(toFriendlyMessage(err))`，UI 不跳转 |
| **Query 错误 + 组件判断** | GET 失败（404/网络/500） | 渲染 `<ErrorState>` + Retry（调 `refetch()`） |
| **根 `ErrorBoundary`** | React 渲染异常 | fallback 页 + Reload 按钮；dev 展示 stack |
| **Router `errorComponent`** | 路由解析 / `validateSearch` 失败 | 自动回落到无筛选默认 search params |

**v1 无 auth**：不处理 401/403。未来如果加就在 `api/client.ts` 的 `onResponse` middleware 拦。

## 9. 测试策略

**M2c-1 不引入 Vitest / Testing Library**。理由：

- CLI 与 service 层已有 TDD 覆盖（`tests/unit/`、`tests/api/`、`tests/cli/`）是业务正确性的真实守门员
- 前端 M2c-1 都是"组合层"代码，测试 ROI 低
- M2c-3 加表单（动态 `custom_fields` 校验、SN 查重、错误映射）后一次性引入 Vitest，这时测试才有抓手

本里程碑的**质量抓手**：

1. `pnpm --dir frontend build` 必须过（tsc + vite）
2. `pnpm --dir frontend lint` 必须过
3. `frontend-design` skill 三个 review 节点（见 §3.4）
4. 手工烟测清单（附录 A）

M2c-3 引入 Vitest 时，同步补"测试基础设施"（vite config、setup、jsdom）。

## 10. 交付清单（Definition of Done）

**基础设施**
- [ ] `design-system/asset-hub/MASTER.md` + `pages/assets-list.md` 已 commit（✓ brainstorm 阶段已完成）
- [ ] `gen:api` 脚本可用；`schema.d.ts` 从后端生成并 commit
- [ ] `api/client.ts` + `api/query-client.ts` + `query-keys.ts` + `api/hooks/assets.ts` + `api/hooks/types.ts` 齐备
- [ ] 根 `ErrorBoundary` 挂载，路由 `errorComponent` 兜底

**主题与字体（§3.5.3 / §6）**
- [ ] `@fontsource-variable/geist` 已移除；`fira-code` + `fira-sans` 装载
- [ ] `globals.css` `@theme` 段主字体 = Fira Sans，heading/mono = Fira Code；中文 fallback = PingFang SC / Microsoft YaHei UI（非 system-ui）
- [ ] `globals.css` 用 MASTER 的 token 替换；light/dark 对比度 ≥4.5:1（`frontend-design` review ④-1）
- [ ] `AppLayout` + `ThemeProvider` + `ThemeToggle` + 防闪烁脚本联通；Light / Dark / System 三态持久化；默认 light；首屏不闪

**列表页与审美承诺（§3.5）**
- [ ] 列表页：筛选 + 排序 + 分页 + 列显隐 + URL-sync + 空/错/载态全覆盖（`frontend-design` review ④-2）
- [ ] `StatusBadge` 4 态 light/dark 各达 4.5:1；与 Primary/CTA 视觉不撞脸
- [ ] §3.5.5 Motion 3 个时刻**全部实现**：首屏 stagger reveal / 筛选淡切 / pill 色变；`prefers-reduced-motion` 生效降级
- [ ] §3.5.5 全局禁用项**无一出现**：无 hover 放大、无背景动画、无路由进场动画、无 >400ms 过渡、无 spinner
- [ ] §3.5.6 Depth 守则遵守：无 glassmorphism、无多层 drop shadow、hover 走色温差
- [ ] §3.5.7 shadcn 首次引入的组件**全部**完成 variant 审查与色值替换
- [ ] 数字列启用 `font-feature-settings: "tnum"`；`asset_code / serial_number` 列局部 Fira Code

**质量抓手**
- [ ] 后端不变；`tests/` 全部绿
- [ ] 手工烟测清单（附录 A）全过
- [ ] `frontend-design` skill 合并前最终 review ④-3 通过（Pre-Delivery Checklist 逐项勾选）
- [ ] `pnpm build` / `pnpm lint` 通过

## 11. 开放决策（等 plan 阶段 / review 敲定）

- `globals.css` 中 `.dark` 变量的具体 `oklch()` 值：由 MASTER 色相 × shadcn dark 亮度曲线推导 + `frontend-design` review 拍板
- 4 条语义状态色（light/dark 各一套）的具体色值：同上，附加"对比度 ≥4.5:1 且 4 态彼此可区分"硬约束
- `EmptyState` 的图标 / 插画风格：MASTER 驱动 + `frontend-design` 校
- 表格行高、表头高、分隔线风格、hover 背景：按 MASTER "Data-Dense" 精神定（紧凑），实施期根据 pages/assets-list.md "Content Density: High" 推导
- Pre-Delivery Checklist 中"cursor-pointer / 150-300ms transitions / focus-visible ring"等实现细节：实施期 Task 内自查
- 初始 shadcn 组件的 variant 定制（尤其 button / input / badge）：MASTER 的 Primary/CTA 色注入后回归官方 variant 即可

## 12. 后续里程碑索引

- M2c-2 · 详情 + 流转：复用本里程碑的 `AppLayout / api layer / theme / feedback 组件`；新增 `/assets/:id` 路由、派发/归还对话框、流转时间线、附件查看
- M2c-3 · 表单 + 附件上传：新增 `/assets/new` 和 `/assets/:id/edit`；动态 `custom_fields` 渲染；附件上传 UI；**本里程碑同步引入 Vitest + Testing Library**
- M3 · 特性完整：`/dashboard` 4 图 + `GET /api/stats`、导出按钮 + `GET /api/export`、类型管理 UI、批量操作
- M4 · UI 打磨：审美打磨、命令面板（⌘K）、响应式、微动效、dark 模式审美打磨

---

## 附录 A · 手工烟测清单（合并前必过）

1. **空数据库**：清空 `data/asset_hub.db` 后启动，`/` 显示 `EmptyState`（不是错误态）
2. **后端未启**：kill 后端，刷新 `/`，显示 `ErrorState` + Retry；点 Retry 前先把后端拉起，再点 → 成功
3. **筛选 URL 同步**：依次勾 type → status → holder → q → 点排序表头 → 翻页 → 复制 URL → 新 tab 打开 → 结果一致
4. **刷新保留筛选**：应用一组筛选后浏览器刷新，所有筛选条件保留
5. **改筛选回第 1 页**：先翻到第 3 页，再改 status，自动回第 1 页
6. **列显隐持久化**：关掉几列 → 刷新 → 保留；换浏览器 tab → 独立
7. **主题三态切换**：Light → Dark → System；每次切换**无闪烁**；刷新保留；System 模式下改系统配色响应
8. **q 输入防抖**：连续打字，Network 里应只有最后一次 `/api/assets` 请求
9. **行点击跳详情**：点一行 → 跳 `/assets/<uuid>` → 显示 Router 默认 404 占位（本里程碑预期）
10. **⋯ 菜单**：所有动作 disabled 且有 tooltip 说明"即将在 M2c-2/3 开放"
11. **4.5:1 对比度**：Chrome DevTools Lighthouse Accessibility 跑一次，`/` 路由 Score ≥95
12. **>2000 条告警**：写一个临时 seed 脚本造 2001 条资产，进 `/` 控制台有 warn（可选，跳过也行）
13. **字体审计（§3.5.3）**：DevTools Computed → Font Family，页面任意 body 文字渲染字体应为 `Fira Sans`，编号字段为 `Fira Code`；**若看到 Inter / Roboto / system-ui / Geist 视为失败**
14. **Motion 3 时刻（§3.5.5）**：
    - 强制刷新 `/`，观察前 20 行是否 stagger 淡入（按住 DevTools Performance 记录验证 ≤400ms 内全部就位）
    - 切 filter，观察 `<tbody>` 是否 opacity+translateY 120-160ms 切换
    - 如果有可造状态切换的资产（M2c-2 之前可直接改 DB），pill 色变 150ms 可见
    - 系统设置中开启"减少动画"（Windows / macOS），三个时刻全部降为瞬时切换
15. **反模式扫（§3.5.5 / §3.5.6）**：
    - 按钮 hover 不放大（无 `transform: scale`）
    - 无 `animate-spin`、无 `backdrop-filter: blur`、无渐变背景
    - 表格 hover 行背景仅色温变化，无外层 shadow

## 附录 B · ui-ux-pro-max 生成物引用

- MASTER：`design-system/asset-hub/MASTER.md`
- 列表页覆盖：`design-system/asset-hub/pages/assets-list.md`
- Brainstorm 使用的关键词：
  - MASTER：`internal admin dashboard panel data dense professional`
  - 列表页：`admin inventory crud drill-down data grid list`
- **忽略的模板噪声**：Project Grid Masonry / Hero Name-Role / Contact CTA / 3D models & textures / Video loops / Multi-select bulk edit（最后一项与 D5 冲突）

## 附录 C · 与总设计文档的对齐点

- §3 技术选型：React + Vite + TanStack Router + TanStack Table + Tailwind + shadcn 全部采用
- §3 openapi-fetch vs @hey-api/openapi-ts "Plan 阶段择优" → **本 spec 定为 D2: openapi-fetch**
- §7.1 页面清单：本里程碑交付"资产列表（首页）"1 个；其余推到 M2c-2 / M2c-3 / M3
- §7.2 设计原则：遵守 `frontend-design` skill，避免 AI 模板脸 → 在 §3.4 作为三个 review 闸门强制执行
- §7.3 前后端交互：openapi-typescript 生成类型、Vite 代理 `/api`、生产 `StaticFiles` 托管 `dist` → 按此执行
- §13 选型待观察项：本里程碑不翻 `SQLModel` 与 `Tremor`
