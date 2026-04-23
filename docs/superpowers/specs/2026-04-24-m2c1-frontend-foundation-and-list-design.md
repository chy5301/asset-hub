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

### 3.4 `frontend-design` skill 的 review 闸门（必经）

实施期三个节点必须调用 `frontend-design` skill 做 review：

1. **`globals.css` 写好后** —— 配色、语义色、对比度、反模式扫
2. **`AssetListPage` 骨架可跑后** —— 布局 / 信息层级 / 空态 / 错态 / 反"AI 模板脸"
3. **M2c-1 合并前** —— 整体审美 + 反模式最终扫 + Pre-Delivery Checklist（见 MASTER）

Review 发现的偏差**回写** `design-system/asset-hub/MASTER.md` 或 page override 作为"实战纠偏备注"，形成闭环。

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

shadcn 组件按需 `pnpm dlx shadcn@latest add <name>` 生成，最小集：`button / input / select / table / badge / dropdown-menu / skeleton / separator / tooltip / sonner`。

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

- `:root`（light）以 MASTER 的 `#F8FAFC / #1E40AF / #1E3A8A` 为锚，按 shadcn 变量名填充；**不改变量名**，让所有 shadcn 组件自动跟随
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

### 6.5 字体接入

- Fira Code / Fira Sans 通过 `@fontsource-variable/*` 按需装（替换现有的 Geist）
- 中文 fallback 链：`"PingFang SC", "Microsoft YaHei UI", system-ui, sans-serif`
- 数字等宽：列表表格数字列启用 `font-feature-settings: "tnum"`，**不**整列换等宽字体
- 等宽仅用于：`asset_code` / `serial_number` 等编号字段

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

状态语义映射集中于 `src/features/assets/status-labels.ts`：

```ts
export const STATUS_META: Record<AssetStatus, { label: string; token: string; dot: string }> = {
  IN_USE:      { label: "在用",  token: "var(--status-in-use)",      dot: "●" },
  IDLE:        { label: "闲置",  token: "var(--status-idle)",        dot: "○" },
  MAINTENANCE: { label: "维护",  token: "var(--status-maintenance)", dot: "⚠" },
  RETIRED:     { label: "报废",  token: "var(--status-retired)",     dot: "—" },
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

- [ ] `design-system/asset-hub/MASTER.md` + `pages/assets-list.md` 生成并 commit（✓ brainstorm 阶段已完成）
- [ ] `globals.css` 用 MASTER 的 token 替换，light/dark 对比度达标（`frontend-design` review ①）
- [ ] `AppLayout` + `ThemeProvider` + `ThemeToggle` + 防闪烁脚本联通，三态持久化正常，首屏不闪
- [ ] `gen:api` 脚本可用；`schema.d.ts` 从后端生成并 commit
- [ ] `api/client.ts` + `api/query-client.ts` + `query-keys.ts` + `api/hooks/assets.ts` + `api/hooks/types.ts` 齐备
- [ ] 列表页：筛选 + 排序 + 分页 + 列显隐 + URL-sync + 空/错/载态全覆盖（`frontend-design` review ②）
- [ ] `StatusBadge` 4 态 light/dark 各达 4.5:1
- [ ] 根 `ErrorBoundary` 挂载，路由 `errorComponent` 兜底
- [ ] 后端不变；`tests/` 全部绿
- [ ] 手工烟测清单（附录 A）全过
- [ ] `frontend-design` skill 合并前最终 review ③ 通过
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
