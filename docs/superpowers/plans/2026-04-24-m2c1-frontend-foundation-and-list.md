# M2c-1 · 前端地基 + 资产列表页 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 基于 `docs/superpowers/specs/2026-04-24-m2c1-frontend-foundation-and-list-design.md`，交付可交互的 `/` 资产列表页 + 所有后续里程碑（M2c-2/M2c-3）共享的前端地基（工具链、数据层、主题、布局壳）。

**Architecture:** 严格按 spec §4 三层分离，数据层集中 `src/api/*`（业务代码只经 hooks 访问）；URL 是筛选真相（TanStack Router typed search + Zod）；主题 light-first 三态；**§3.5 审美纲领**在每个 UI Task 内落实并显式引用。**无 Vitest**（spec §9）——每 Task 验证 = `pnpm build` + `pnpm lint` + 手工观察。

**Tech Stack:** React 19 + Vite + TypeScript strict + TanStack Router/Query/Table + openapi-fetch/typescript + Zod + shadcn（radix-nova style）+ sonner + Fira Code/Sans（@fontsource-variable）+ lucide-react + pnpm

**Spec 引用约定：** 每个 UI-ish Task 末尾的 `**§3.5 约束引用**` 栏列出该 Task 必须满足的 spec 条目（spec §3.4 强制要求）。

---

## 文件结构

M2c-1 完成后前端新增/修改的文件：

```
frontend/
├── package.json                             # 修改：+deps（fira, tanstack, openapi, zod, sonner）/-geist
├── index.html                               # 修改：<title>、<html lang>、防闪烁脚本
├── scripts/
│   └── gen-openapi.ts                       # 新增：生成 schema.d.ts
└── src/
    ├── main.tsx                             # 修改：包 QueryClientProvider + ThemeProvider
    ├── routes/
    │   ├── __root.tsx                       # 修改：AppLayout + Devtools
    │   └── index.tsx                        # 修改：AssetListPage 薄壳 + 组合子组件
    ├── api/
    │   ├── generated/schema.d.ts            # 新：openapi-typescript 产物
    │   ├── client.ts                        # 新：openapi-fetch 实例
    │   ├── query-client.ts                  # 新：QueryClient + 默认 options
    │   ├── query-keys.ts                    # 新：集中 key factory
    │   └── hooks/
    │       ├── types.ts                     # 新：useAssetTypesQuery
    │       └── assets.ts                    # 新：useAssetsQuery + CRUD mutations
    ├── lib/
    │   ├── error.ts                         # 新：toFriendlyMessage / isHttpError
    │   └── debounce.ts                      # 新：轻量 debounce
    ├── components/
    │   ├── layout/app-layout.tsx            # 新
    │   ├── theme/
    │   │   ├── theme-provider.tsx           # 新
    │   │   └── theme-toggle.tsx             # 新
    │   ├── feedback/
    │   │   ├── error-boundary.tsx           # 新
    │   │   ├── empty-state.tsx              # 新
    │   │   ├── error-state.tsx              # 新
    │   │   └── skeleton-row.tsx             # 新
    │   ├── status/status-badge.tsx          # 新
    │   └── ui/                              # shadcn 按需 add（Task 2）
    ├── features/assets/
    │   ├── status-labels.ts                 # 新：STATUS_META（Lucide Icon）
    │   └── list/
    │       ├── search-schema.ts             # 新：Zod search params
    │       ├── assets-filters.tsx           # 新
    │       ├── column-visibility.tsx        # 新
    │       ├── assets-table.tsx             # 新
    │       └── assets-pagination.tsx        # 新
    └── styles/globals.css                   # 修改：tokens + radius + status-* + 字体
```

后端**零改动**。

---

## Task 1: 依赖切换（字体 + 数据层 + 辅助库）

**Files:**
- Modify: `frontend/package.json`

- [ ] **Step 1：在 `frontend/package.json` 替换字体包、增数据层依赖**

按 spec §4.3 改：

```jsonc
// dependencies：加 fira，保留既有 shadcn 相关
"@fontsource/fira-code": "^5.2.7",
"@fontsource/fira-sans": "^5.2.7",
"@tanstack/react-query": "^5.60.0",
"@tanstack/react-table": "^8.20.0",
"openapi-fetch": "^0.12.0",
"sonner": "^1.7.0",
"zod": "^3.23.8",

// devDependencies：加
"@tanstack/react-query-devtools": "^5.60.0",
"openapi-typescript": "^7.4.0",
"tsx": "^4.19.0"
```

**移除** `@fontsource-variable/geist`（§3.5.3 反通用字体审计）。

> **字体包命名说明（2026-04-24 实施期纠正）**：Fira Sans 在 Google Fonts 上**没有 variable 字体发布**（`@fontsource-variable/fira-sans` 在 npm 上 404）；只有 Fira Code 有 variable（`@fontsource-variable/fira-code@5.2.7`）。为保持两种字体的包约定一致、避免 globals.css 里混用两种 font-family 字面量，**本里程碑统一用 `@fontsource/*`（静态字体包）**。Bundle 相比理论最优 variable 版本增大 ~100KB，放到 M4 UI 打磨期再评估。spec §3.5.3 / §6.5 同步修订。

> **openapi-typescript peer-dep 说明（2026-04-24）**：`openapi-typescript@7.13.0`（以及所有 7.x）声明 `peerDependencies: { typescript: "^5.x" }`，而项目 TypeScript `~6.0.2`。实施期已做冒烟测：`pnpm exec openapi-typescript --help` 在 TS 6.0.2 环境下正常加载、binary 启动无异常。peer 约束是保守 range（TS 公共 API 在 5→6 向后兼容），**不阻塞** Task 3 gen-openapi 脚本运行。如果 Task 3 实际执行时发现运行时错误，回到此处评估——upgrade openapi-typescript 到支持 TS 6.x 的版本，或临时降 TypeScript 到 5.x（风险：TanStack Router strict null checks 可能相应失效）。

- [ ] **Step 2：安装依赖**

```bash
pnpm --dir frontend install
```

Expected：lockfile 更新，`node_modules/` 补齐。

- [ ] **Step 3：验证 build 仍通过**

```bash
pnpm --dir frontend build
```

Expected：PASS。如因 globals.css 已 `@import "@fontsource-variable/geist"` 而报错，先打开 `frontend/src/styles/globals.css`，把 `@import "@fontsource-variable/geist";` 改成：

```css
@import "@fontsource/fira-code";
@import "@fontsource/fira-sans";
```

再次 `pnpm --dir frontend build`。

- [ ] **Step 4：commit**

```bash
git add frontend/package.json frontend/pnpm-lock.yaml frontend/src/styles/globals.css
git commit -m "chore(frontend): 切 Fira Code + Fira Sans，补齐 TanStack Query/Table + openapi 工具链"
```

---

## Task 2: 初始化 shadcn 组件最小集

**Files:**
- Create (via shadcn CLI): `frontend/src/components/ui/{button,input,select,table,badge,dropdown-menu,skeleton,separator,tooltip,sonner}.tsx`

> 说明：`components.json` 已配置好（`style: radix-nova`, `iconLibrary: lucide`, alias `@`）。本 Task 只负责 scaffold；§3.5.7 要求的 variant 重调在 **Task 12** 统一完成（那时 globals.css 已注入新 tokens，重调才有参考点）。

- [ ] **Step 1：按最小集顺序 add**

```bash
pnpm --dir frontend dlx shadcn@latest add button input select table badge dropdown-menu skeleton separator tooltip sonner
```

Expected：`frontend/src/components/ui/` 下生成 10 个 `.tsx` 文件。如果 CLI 交互询问覆盖，一律选 "yes"。

- [ ] **Step 2：验证 build 通过**

```bash
pnpm --dir frontend build
```

Expected：PASS。

- [ ] **Step 3：commit**

```bash
git add frontend/src/components/ui/ frontend/package.json frontend/pnpm-lock.yaml frontend/components.json
git commit -m "chore(frontend): scaffold shadcn 最小组件集（variant 定制留 Task 12）"
```

---

## Task 3: OpenAPI 类型生成脚本与首次产出

**Files:**
- Create: `frontend/scripts/gen-openapi.ts`
- Modify: `frontend/package.json`（加 `gen:api` script）
- Create: `frontend/src/api/generated/schema.d.ts`（生成产物）

- [ ] **Step 1：写生成脚本**

创建 `frontend/scripts/gen-openapi.ts`：

```ts
import fs from "node:fs/promises";
import path from "node:path";
import openapiTS, { astToString } from "openapi-typescript";

const OPENAPI_URL = process.env.OPENAPI_URL ?? "http://localhost:8000/openapi.json";
const OUT = path.resolve("src/api/generated/schema.d.ts");

async function main() {
  console.log(`[gen-openapi] fetching ${OPENAPI_URL}`);
  const ast = await openapiTS(new URL(OPENAPI_URL));
  const body = astToString(ast);
  await fs.mkdir(path.dirname(OUT), { recursive: true });
  await fs.writeFile(OUT, body, "utf8");
  console.log(`[gen-openapi] wrote ${OUT} (${body.length} bytes)`);
}

main().catch((err) => {
  console.error("[gen-openapi] failed:", err);
  process.exit(1);
});
```

- [ ] **Step 2：在 `frontend/package.json` 加 scripts**

```jsonc
"scripts": {
  "dev": "vite",
  "build": "tsc -b && vite build",
  "lint": "eslint .",
  "preview": "vite preview",
  "gen:api": "tsx scripts/gen-openapi.ts"
}
```

- [ ] **Step 3：启动后端（**需手动**，另一个终端）**

```bash
uv run uvicorn asset_hub.api.app:app --reload --port 8000
```

验证 `http://localhost:8000/openapi.json` 可访问。

- [ ] **Step 4：跑生成**

```bash
pnpm --dir frontend gen:api
```

Expected：打印 `wrote .../src/api/generated/schema.d.ts (<bytes>)`。打开该文件确认包含 `/api/assets`、`/api/types`、`/api/assets/{asset_id}/attachments` 等 path 定义。

- [ ] **Step 5：验证 build**

```bash
pnpm --dir frontend build
```

Expected：PASS。

- [ ] **Step 6：commit**

```bash
git add frontend/scripts/gen-openapi.ts frontend/package.json frontend/src/api/generated/
git commit -m "feat(frontend): OpenAPI 类型生成脚本 + 首次产出 schema.d.ts"
```

---

## Task 4: 数据层基础设施（client / query-client / query-keys / 错误映射）

**Files:**
- Create: `frontend/src/api/client.ts`
- Create: `frontend/src/api/query-client.ts`
- Create: `frontend/src/api/query-keys.ts`
- Create: `frontend/src/lib/error.ts`
- Create: `frontend/src/lib/debounce.ts`

- [ ] **Step 1：`src/api/client.ts`**

```ts
import createClient from "openapi-fetch";
import type { paths } from "./generated/schema";

export const http = createClient<paths>({ baseUrl: "/" });
```

- [ ] **Step 2：`src/lib/error.ts`**

```ts
export interface HttpErrorShape {
  status: number;
  detail?: string;
}

export function isHttpError(err: unknown): err is HttpErrorShape {
  return (
    typeof err === "object" &&
    err !== null &&
    typeof (err as { status?: unknown }).status === "number"
  );
}

const STATUS_MESSAGES: Record<number, string> = {
  404: "资产不存在或已被删除",
  409: "请求冲突",
  422: "数据校验失败",
};

export function toFriendlyMessage(err: unknown): string {
  if (isHttpError(err)) {
    if (err.status === 409 && err.detail) return err.detail;
    if (err.status === 422 && err.detail) return `数据校验失败：${err.detail}`;
    if (err.status >= 500) return "服务端错误，请稍后重试";
    return STATUS_MESSAGES[err.status] ?? `请求失败（HTTP ${err.status}）`;
  }
  if (err instanceof Error && err.message.includes("fetch")) {
    return "网络请求失败，请检查后端是否运行";
  }
  return "未知错误";
}

/** Wrap openapi-fetch 的 { data, error, response } 响应，失败时抛 HttpErrorShape。 */
export function unwrap<T>(result: {
  data?: T;
  error?: unknown;
  response: Response;
}): T {
  if (result.error || !result.data) {
    const detail =
      typeof result.error === "object" && result.error !== null
        ? (result.error as { detail?: string }).detail
        : undefined;
    const err: HttpErrorShape = { status: result.response.status, detail };
    throw err;
  }
  return result.data;
}
```

- [ ] **Step 3：`src/api/query-client.ts`**

```ts
import { QueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { isHttpError, toFriendlyMessage } from "@/lib/error";

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      refetchOnWindowFocus: false,
      retry: (failCount, err) => {
        if (isHttpError(err) && err.status >= 400 && err.status < 500) return false;
        return failCount < 2;
      },
    },
    mutations: {
      onError: (err) => toast.error(toFriendlyMessage(err)),
    },
  },
});
```

- [ ] **Step 4：`src/api/query-keys.ts`**

```ts
import type { AssetsSearch } from "@/features/assets/list/search-schema";

export const qk = {
  assets: {
    all: ["assets"] as const,
    list: (params: AssetsSearch) => ["assets", "list", params] as const,
    detail: (id: string) => ["assets", "detail", id] as const,
  },
  assetTypes: {
    all: ["assetTypes"] as const,
    list: () => ["assetTypes", "list"] as const,
  },
} as const;
```

> 注：`AssetsSearch` 类型在 Task 14 定义；本 Task 先 import，TypeScript 会在 Task 14 之前报 unresolved。**为此先写一个临时占位**：Task 14 再改回真实 import。

**实际 Step 4（临时版）**：

```ts
// src/api/query-keys.ts
type AssetListParams = Record<string, unknown>;

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

Task 14 写 `search-schema.ts` 后回来把 `AssetListParams` 换成 `import type { AssetsSearch } from "@/features/assets/list/search-schema"`。

- [ ] **Step 5：`src/lib/debounce.ts`**

```ts
export function debounce<A extends unknown[]>(
  fn: (...args: A) => void,
  ms: number,
): (...args: A) => void {
  let timer: ReturnType<typeof setTimeout> | null = null;
  return (...args: A) => {
    if (timer) clearTimeout(timer);
    timer = setTimeout(() => fn(...args), ms);
  };
}
```

- [ ] **Step 6：验证 build + lint**

```bash
pnpm --dir frontend build && pnpm --dir frontend lint
```

Expected：PASS。

- [ ] **Step 7：commit**

```bash
git add frontend/src/api/ frontend/src/lib/error.ts frontend/src/lib/debounce.ts
git commit -m "feat(frontend): 数据层基础设施——http client / QueryClient / query-keys / 错误映射"
```

---

## Task 5: asset-types hook（简单，确立模式）

**Files:**
- Create: `frontend/src/api/hooks/types.ts`

- [ ] **Step 1：`src/api/hooks/types.ts`**

```ts
import { useQuery } from "@tanstack/react-query";
import { http } from "@/api/client";
import { qk } from "@/api/query-keys";
import { unwrap } from "@/lib/error";

export function useAssetTypesQuery() {
  return useQuery({
    queryKey: qk.assetTypes.list(),
    staleTime: Infinity, // 类型字典几乎不变
    queryFn: async () => {
      const res = await http.GET("/api/types");
      return unwrap(res);
    },
  });
}
```

> 如果生成的 `schema.d.ts` 里端点名不完全是 `/api/types`（请以 Task 3 生成的实际值为准），调整 path 字符串。可用 Grep `"/api/` schema.d.ts 核实。

- [ ] **Step 2：验证 build**

```bash
pnpm --dir frontend build
```

Expected：PASS。若 TS 报 openapi-fetch 路径签名不匹配，核对 `schema.d.ts` 中路径字面量并改 `http.GET("...")` 字符串。

- [ ] **Step 3：commit**

```bash
git add frontend/src/api/hooks/types.ts
git commit -m "feat(frontend): useAssetTypesQuery（staleTime=Infinity，类型字典缓存）"
```

---

## Task 6: assets hooks（list + CRUD mutations，按钮接线留后续里程碑）

**Files:**
- Create: `frontend/src/api/hooks/assets.ts`

> 本 Task 只定义 hook，**不**在任何 UI 中调用 mutation（按钮接线按 spec §5.4 分散到 M2c-2/M2c-3）。`useAssetsQuery` 会在 Task 14 的 AssetListPage 里用。

- [ ] **Step 1：`src/api/hooks/assets.ts`**

```ts
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { http } from "@/api/client";
import { qk } from "@/api/query-keys";
import { unwrap } from "@/lib/error";
import type { AssetsSearch } from "@/features/assets/list/search-schema";

/** 只把后端接受的 filter 参数传过去；sort/page/pageSize 是客户端语义。 */
function toServerParams(search: AssetsSearch) {
  const params: Record<string, string> = {};
  if (search.type) params.type_id = search.type;
  if (search.status) params.status = search.status;
  if (search.holder) params.holder = search.holder;
  if (search.q) params.q = search.q;
  return params;
}

export function useAssetsQuery(search: AssetsSearch) {
  return useQuery({
    queryKey: qk.assets.list(search),
    queryFn: async () => {
      const res = await http.GET("/api/assets", {
        params: { query: toServerParams(search) },
      });
      return unwrap(res);
    },
  });
}

export function useCreateAsset() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: {
      asset_code?: string;
      serial_number?: string;
      name: string;
      type_id: string;
      status?: string;
      holder?: string;
      location?: string;
      notes?: string;
      custom_data?: Record<string, unknown>;
    }) => {
      const res = await http.POST("/api/assets", { body });
      return unwrap(res);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: qk.assets.all });
      toast.success("资产已登记");
    },
  });
}

export function useUpdateAsset(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: Record<string, unknown>) => {
      const res = await http.PATCH("/api/assets/{asset_id}", {
        params: { path: { asset_id: id } },
        body,
      });
      return unwrap(res);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: qk.assets.all });
      toast.success("资产已更新");
    },
  });
}

export function useDeleteAsset() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      const res = await http.DELETE("/api/assets/{asset_id}", {
        params: { path: { asset_id: id } },
      });
      return unwrap(res);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: qk.assets.all });
      toast.success("资产已删除");
    },
  });
}
```

> 字段签名以 Task 3 生成的 `schema.d.ts` 实际字段为准；若与后端 `AssetCreate / AssetUpdate` 签名不符，**改 `body` 类型到匹配 `schema["components"]["schemas"]["AssetCreate"]`** 形式（或直接 import 生成的 `components["schemas"]["AssetCreate"]`）。

- [ ] **Step 2：验证 build（TS 会报 `AssetsSearch` 未定义）**

```bash
pnpm --dir frontend build
```

Expected：**预期失败**（`AssetsSearch` 在 Task 14 才定义）。先跳过，Task 14 完成后再回头验证。

- [ ] **Step 3：添加 `@ts-expect-error` 桩（可选，避免打断后续 build）**

如果中间 build 失败影响后续 Task 的本地开发，临时在 `src/api/hooks/assets.ts` 顶部改成：

```ts
// TEMPORARY: will be replaced in Task 14 after search-schema.ts exists
type AssetsSearch = {
  type?: string;
  status?: "IN_USE" | "IDLE" | "MAINTENANCE" | "RETIRED";
  holder?: string;
  q?: string;
  sort?: string;
  page: number;
  pageSize: number;
};
```

Task 14 完成后改回 `import type { AssetsSearch } from "@/features/assets/list/search-schema"`。

- [ ] **Step 4：再次 build 通过**

```bash
pnpm --dir frontend build
```

Expected：PASS。

- [ ] **Step 5：commit**

```bash
git add frontend/src/api/hooks/assets.ts
git commit -m "feat(frontend): assets hooks——list + CRUD mutations（临时 AssetsSearch 在 Task 14 替换）"
```

---

## Task 7: `globals.css` 全面改造（tokens + 字体 + radius + 状态语义色）

**Files:**
- Modify: `frontend/src/styles/globals.css`

**§3.5 约束引用：** §3.5.1（radius ≤6px、直角为主、无渐变）、§3.5.3（Fira 主字体；中文 fallback PingFang SC / Microsoft YaHei UI，禁 system-ui 作主字体）、§3.5.4（dominant+accent 结构：primary navy/70%、text+divider 灰/25%、amber CTA/<5%）、§3.5.6（1px hairline、禁多层 shadow）。

- [ ] **Step 1：完整重写 `frontend/src/styles/globals.css`**

```css
@import "tailwindcss";
@import "tw-animate-css";
@import "shadcn/tailwind.css";
@import "@fontsource/fira-code";
@import "@fontsource/fira-sans";

@custom-variant dark (&:is(.dark *));

@theme inline {
  /* 字体（§3.5.3） */
  --font-sans: "Fira Sans", "PingFang SC", "Microsoft YaHei UI", sans-serif;
  --font-heading: "Fira Sans", "PingFang SC", "Microsoft YaHei UI", sans-serif;
  --font-mono: "Fira Code", ui-monospace, monospace;

  /* shadcn 色变量（§3.5.4 dominant+accent 结构由值本身保证） */
  --color-sidebar-ring: var(--sidebar-ring);
  --color-sidebar-border: var(--sidebar-border);
  --color-sidebar-accent-foreground: var(--sidebar-accent-foreground);
  --color-sidebar-accent: var(--sidebar-accent);
  --color-sidebar-primary-foreground: var(--sidebar-primary-foreground);
  --color-sidebar-primary: var(--sidebar-primary);
  --color-sidebar-foreground: var(--sidebar-foreground);
  --color-sidebar: var(--sidebar);
  --color-chart-5: var(--chart-5);
  --color-chart-4: var(--chart-4);
  --color-chart-3: var(--chart-3);
  --color-chart-2: var(--chart-2);
  --color-chart-1: var(--chart-1);
  --color-ring: var(--ring);
  --color-input: var(--input);
  --color-border: var(--border);
  --color-destructive: var(--destructive);
  --color-accent-foreground: var(--accent-foreground);
  --color-accent: var(--accent);
  --color-muted-foreground: var(--muted-foreground);
  --color-muted: var(--muted);
  --color-secondary-foreground: var(--secondary-foreground);
  --color-secondary: var(--secondary);
  --color-primary-foreground: var(--primary-foreground);
  --color-primary: var(--primary);
  --color-popover-foreground: var(--popover-foreground);
  --color-popover: var(--popover);
  --color-card-foreground: var(--card-foreground);
  --color-card: var(--card);
  --color-foreground: var(--foreground);
  --color-background: var(--background);

  /* 状态语义色（§6.2 扩展；§3.5.4 要求与 Primary/CTA 不撞脸） */
  --color-status-in-use: var(--status-in-use);
  --color-status-idle: var(--status-idle);
  --color-status-maintenance: var(--status-maintenance);
  --color-status-retired: var(--status-retired);
  --color-status-in-use-fg: var(--status-in-use-fg);
  --color-status-idle-fg: var(--status-idle-fg);
  --color-status-maintenance-fg: var(--status-maintenance-fg);
  --color-status-retired-fg: var(--status-retired-fg);

  /* 半径（§3.5.1 ≤6px） */
  --radius-sm: calc(var(--radius) * 0.6);
  --radius-md: calc(var(--radius) * 0.8);
  --radius-lg: var(--radius);
  --radius-xl: calc(var(--radius) * 1.4);
}

/* ===== Light 模式（默认，§3.5.4 以 MASTER tokens 为锚） ===== */
:root {
  /* Background / foreground：MASTER bg #F8FAFC / text #1E3A8A */
  --background: oklch(0.984 0.004 247);   /* ≈ #F8FAFC slate-50 */
  --foreground: oklch(0.262 0.093 261);   /* ≈ #1E3A8A navy-900 */

  --card: oklch(1 0 0);                   /* 纯白卡面 */
  --card-foreground: oklch(0.262 0.093 261);
  --popover: oklch(1 0 0);
  --popover-foreground: oklch(0.262 0.093 261);

  /* Primary：MASTER #1E40AF navy-800；Foreground 用近白 */
  --primary: oklch(0.343 0.171 264);
  --primary-foreground: oklch(0.985 0 0);

  /* Secondary：低饱和灰 */
  --secondary: oklch(0.95 0.008 247);
  --secondary-foreground: oklch(0.262 0.093 261);

  --muted: oklch(0.95 0.008 247);
  --muted-foreground: oklch(0.48 0.017 247);

  --accent: oklch(0.92 0.012 247);
  --accent-foreground: oklch(0.262 0.093 261);

  --destructive: oklch(0.58 0.22 27);     /* 红色 */

  --border: oklch(0.9 0.01 247);          /* 1px hairline */
  --input: oklch(0.9 0.01 247);
  --ring: oklch(0.343 0.171 264);         /* focus ring = primary */

  /* CTA（amber #F59E0B）单独变量，不进 shadcn 默认 ——仅在"真正的关键动作"使用 */
  --cta: oklch(0.75 0.16 75);
  --cta-foreground: oklch(0.262 0.093 261);

  /* 状态语义色（light；§3.5.4 不与 primary/cta 撞脸） */
  --status-in-use: oklch(0.92 0.08 155);       /* 柔绿背景 */
  --status-in-use-fg: oklch(0.38 0.14 150);    /* 深绿前景 */
  --status-idle: oklch(0.94 0.015 247);        /* 冷中性背景 */
  --status-idle-fg: oklch(0.45 0.03 247);      /* 深冷灰前景 */
  --status-maintenance: oklch(0.93 0.09 65);   /* 柔橙背景（不同于 cta 色相） */
  --status-maintenance-fg: oklch(0.42 0.14 55);
  --status-retired: oklch(0.93 0.005 247);     /* 极低饱和灰 */
  --status-retired-fg: oklch(0.50 0.008 247);

  /* Chart：蓝系渐变 */
  --chart-1: oklch(0.343 0.171 264);
  --chart-2: oklch(0.55 0.15 255);
  --chart-3: oklch(0.70 0.12 240);
  --chart-4: oklch(0.80 0.08 230);
  --chart-5: oklch(0.85 0.05 220);

  /* Radius（§3.5.1 ≤6px） */
  --radius: 0.375rem;

  /* Sidebar 变量（shadcn 要求齐备） */
  --sidebar: oklch(0.984 0.004 247);
  --sidebar-foreground: oklch(0.262 0.093 261);
  --sidebar-primary: oklch(0.343 0.171 264);
  --sidebar-primary-foreground: oklch(0.985 0 0);
  --sidebar-accent: oklch(0.92 0.012 247);
  --sidebar-accent-foreground: oklch(0.262 0.093 261);
  --sidebar-border: oklch(0.9 0.01 247);
  --sidebar-ring: oklch(0.343 0.171 264);
}

/* ===== Dark 模式（独立调，不做 light 反转，§3.5.4） ===== */
.dark {
  --background: oklch(0.14 0.02 258);         /* 深 navy/slate 底 */
  --foreground: oklch(0.95 0.01 247);

  --card: oklch(0.18 0.025 258);
  --card-foreground: oklch(0.95 0.01 247);
  --popover: oklch(0.18 0.025 258);
  --popover-foreground: oklch(0.95 0.01 247);

  --primary: oklch(0.62 0.17 255);            /* 亮蓝（dark 下提亮度） */
  --primary-foreground: oklch(0.14 0.02 258);

  --secondary: oklch(0.24 0.03 258);
  --secondary-foreground: oklch(0.95 0.01 247);

  --muted: oklch(0.24 0.03 258);
  --muted-foreground: oklch(0.70 0.02 247);

  --accent: oklch(0.28 0.035 258);
  --accent-foreground: oklch(0.95 0.01 247);

  --destructive: oklch(0.68 0.20 25);

  --border: oklch(1 0 0 / 10%);
  --input: oklch(1 0 0 / 15%);
  --ring: oklch(0.62 0.17 255);

  --cta: oklch(0.72 0.14 75);                 /* dark 下 amber 降亮度 */
  --cta-foreground: oklch(0.14 0.02 258);

  --status-in-use: oklch(0.28 0.08 150);
  --status-in-use-fg: oklch(0.82 0.12 150);
  --status-idle: oklch(0.25 0.015 247);
  --status-idle-fg: oklch(0.75 0.02 247);
  --status-maintenance: oklch(0.30 0.09 60);
  --status-maintenance-fg: oklch(0.85 0.13 65);
  --status-retired: oklch(0.22 0.005 247);
  --status-retired-fg: oklch(0.62 0.008 247);

  --chart-1: oklch(0.62 0.17 255);
  --chart-2: oklch(0.55 0.15 255);
  --chart-3: oklch(0.70 0.12 240);
  --chart-4: oklch(0.55 0.08 230);
  --chart-5: oklch(0.45 0.05 220);

  --sidebar: oklch(0.18 0.025 258);
  --sidebar-foreground: oklch(0.95 0.01 247);
  --sidebar-primary: oklch(0.62 0.17 255);
  --sidebar-primary-foreground: oklch(0.14 0.02 258);
  --sidebar-accent: oklch(0.28 0.035 258);
  --sidebar-accent-foreground: oklch(0.95 0.01 247);
  --sidebar-border: oklch(1 0 0 / 10%);
  --sidebar-ring: oklch(0.62 0.17 255);
}

@layer base {
  * {
    @apply border-border outline-ring/50;
  }
  body {
    @apply bg-background text-foreground;
    /* 数字等宽（§3.5.2） */
    font-feature-settings: "tnum" 1;
  }
  html {
    font-family: var(--font-sans);
  }
  /* 编号字段等宽字体（§3.5.2） */
  .font-code {
    font-family: var(--font-mono);
    font-feature-settings: "tnum" 1, "zero" 1;
  }
  /* focus-visible 显眼方块环（§3.5.2） */
  *:focus-visible {
    outline: 2px solid var(--ring);
    outline-offset: 2px;
    border-radius: 2px;
  }
}

/* ===== Motion 三时刻（§3.5.5） ===== */

/* 时刻 1：首屏表格 stagger reveal */
@layer utilities {
  .stagger-row {
    opacity: 0;
    transform: translateY(4px);
    animation: stagger-row-in 280ms ease-out forwards;
  }
}

@keyframes stagger-row-in {
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* 时刻 2：筛选/分页变更时 tbody 淡切（组件内用 class 控制） */
@layer utilities {
  .tbody-fade {
    animation: tbody-fade-in 140ms ease-out;
  }
}

@keyframes tbody-fade-in {
  from {
    opacity: 0;
    transform: translateY(4px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* prefers-reduced-motion 降级为无动画 */
@media (prefers-reduced-motion: reduce) {
  .stagger-row,
  .tbody-fade {
    animation: none !important;
    opacity: 1 !important;
    transform: none !important;
  }
  *,
  *::before,
  *::after {
    transition-duration: 0.01ms !important;
  }
}
```

- [ ] **Step 2：验证 build**

```bash
pnpm --dir frontend build
```

Expected：PASS。

- [ ] **Step 3：启动 dev server 肉眼核查**

```bash
pnpm --dir frontend dev
```

在浏览器打开 `http://localhost:5173`，应看到：
- 背景色浅灰蓝（slate-50）
- 字体已换成 Fira Sans（标题不再是 Geist 的几何圆润感，改为 Fira 的偏正文风格）
- 现有的 `<h1>asset-hub</h1>` 等文字仍在（下一个 Task 改）

关掉 dev server。

- [ ] **Step 3.5：Dark 模式状态色对比度提前自验**

切到 dark 模式（可临时手工在 html 上加 `class="dark"` 测试），用 Chrome DevTools → Rendering → "Emulate CSS media feature prefers-color-scheme: dark" 进入 dark。

在 Elements 面板选中一个 StatusBadge 样例（可暂时手写一个 demo span 测试 4 态色对），DevTools → Accessibility → Contrast：每对 `(--status-*, --status-*-fg)` 必须 ≥ 4.5:1。

**4 态需各自验证**（light + dark 共 8 组）：

| 组合 | 期望 |
|---|---|
| `--status-in-use` bg × `--status-in-use-fg` fg（light） | ≥4.5:1 |
| `--status-idle` bg × `--status-idle-fg` fg（light） | ≥4.5:1 |
| `--status-maintenance` × `--status-maintenance-fg`（light） | ≥4.5:1 |
| `--status-retired` × `--status-retired-fg`（light） | ≥4.5:1 |
| 以上 4 组在 `.dark` 下各自 | ≥4.5:1 |

**如有不达标**：调对应 oklch 的 L 值（前景更深/背景更浅）后重新验证；**不达标不得进入 Step 4 commit**。

（Task 20 的 Lighthouse 烟测是最终兜底；此处是"早改早省"。）

- [ ] **Step 4：commit**

```bash
git add frontend/src/styles/globals.css
git commit -m "feat(frontend): globals.css 按 §3.5 纲领重写——Fira 字体、MASTER tokens、4 态状态色、radius=0.375rem、Motion 三时刻"
```

---

## Task 8: 防闪烁脚本 + ThemeProvider

**Files:**
- Modify: `frontend/index.html`
- Create: `frontend/src/components/theme/theme-provider.tsx`

**§3.5 约束引用：** D4（默认 light）、§3.5.5（theme 切换本身不动画，直接切 class）。

- [ ] **Step 1：改 `frontend/index.html`（防闪烁 + 品牌 + 中文语言）**

```html
<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="UTF-8" />
    <link rel="icon" type="image/svg+xml" href="/favicon.svg" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>小组资产管理工具</title>
    <script>
      // Anti-flash for dark mode. §6.3 / D4：默认 light，仅当显式 dark 或 system+prefers-dark 才加 .dark class.
      (function () {
        var k = "asset-hub.theme";
        var t = localStorage.getItem(k);
        var prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
        var dark = t === "dark" || (t === "system" && prefersDark);
        if (dark) document.documentElement.classList.add("dark");
      })();
    </script>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

- [ ] **Step 2：创建 `frontend/src/components/theme/theme-provider.tsx`**

```tsx
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";

type Theme = "light" | "dark" | "system";
type Resolved = "light" | "dark";

interface ThemeCtx {
  theme: Theme;
  resolved: Resolved;
  setTheme: (t: Theme) => void;
}

const STORAGE_KEY = "asset-hub.theme";
const Ctx = createContext<ThemeCtx | null>(null);

function computeResolved(theme: Theme): Resolved {
  if (theme === "system") {
    return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  }
  return theme;
}

function applyClass(resolved: Resolved) {
  document.documentElement.classList.toggle("dark", resolved === "dark");
}

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [theme, setThemeState] = useState<Theme>(() => {
    const stored = localStorage.getItem(STORAGE_KEY);
    return (stored === "dark" || stored === "light" || stored === "system" ? stored : "light") as Theme;
  });

  const [resolved, setResolved] = useState<Resolved>(() => computeResolved(theme));

  // 首次挂载：同步一次 class（防闪烁脚本已处理首屏，这里保障 React 水合后一致）
  useEffect(() => {
    applyClass(resolved);
  }, [resolved]);

  // system 模式监听系统变化
  useEffect(() => {
    if (theme !== "system") return;
    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    const onChange = () => setResolved(mq.matches ? "dark" : "light");
    mq.addEventListener("change", onChange);
    return () => mq.removeEventListener("change", onChange);
  }, [theme]);

  const setTheme = useCallback((next: Theme) => {
    setThemeState(next);
    localStorage.setItem(STORAGE_KEY, next);
    setResolved(computeResolved(next));
  }, []);

  const value = useMemo<ThemeCtx>(() => ({ theme, resolved, setTheme }), [theme, resolved, setTheme]);

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useTheme() {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useTheme must be used within ThemeProvider");
  return ctx;
}
```

- [ ] **Step 3：验证 build**

```bash
pnpm --dir frontend build
```

Expected：PASS。

- [ ] **Step 4：commit**

```bash
git add frontend/index.html frontend/src/components/theme/theme-provider.tsx
git commit -m "feat(frontend): 防闪烁脚本 + ThemeProvider（light-first 三态 + localStorage）"
```

---

## Task 9: ThemeToggle

**Files:**
- Create: `frontend/src/components/theme/theme-toggle.tsx`

**§3.5 约束引用：** §3.5.5（全局禁 hover 放大/任何 transform scale）、§3.5.2（focus-visible 方块环由 globals.css 统一承担，此处 button 自动继承）、§3.5.7（Button/DropdownMenu 用 shadcn 基础组件，Task 12 再统一改 variant 色值）。

- [ ] **Step 1：`src/components/theme/theme-toggle.tsx`**

```tsx
import { Laptop, Moon, Sun } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useTheme, type Theme } from "@/components/theme/theme-provider";

const ITEMS: { value: Theme; label: string; Icon: typeof Sun }[] = [
  { value: "light", label: "浅色", Icon: Sun },
  { value: "dark", label: "深色", Icon: Moon },
  { value: "system", label: "跟随系统", Icon: Laptop },
];

export function ThemeToggle() {
  const { theme, setTheme } = useTheme();
  const Current = ITEMS.find((i) => i.value === theme)?.Icon ?? Sun;

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="icon" aria-label="切换主题">
          <Current className="h-4 w-4" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        {ITEMS.map(({ value, label, Icon }) => (
          <DropdownMenuItem
            key={value}
            onSelect={() => setTheme(value)}
            data-active={theme === value}
          >
            <Icon className="mr-2 h-4 w-4" />
            <span>{label}</span>
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
```

> `type Theme` 需从 theme-provider 导出。打开 `theme-provider.tsx`，把 `type Theme = ...` 改成 `export type Theme = ...`。

- [ ] **Step 2：导出 Theme 类型**

修改 `frontend/src/components/theme/theme-provider.tsx` 的第一行 `type` 声明：

```ts
export type Theme = "light" | "dark" | "system";
```

- [ ] **Step 3：验证 build**

```bash
pnpm --dir frontend build
```

Expected：PASS。

- [ ] **Step 4：commit**

```bash
git add frontend/src/components/theme/
git commit -m "feat(frontend): ThemeToggle（Light/Dark/System 三态 dropdown）"
```

---

## Task 10: Feedback 组件（ErrorBoundary / EmptyState / ErrorState / SkeletonRow）

**Files:**
- Create: `frontend/src/components/feedback/error-boundary.tsx`
- Create: `frontend/src/components/feedback/empty-state.tsx`
- Create: `frontend/src/components/feedback/error-state.tsx`
- Create: `frontend/src/components/feedback/skeleton-row.tsx`

**§3.5 约束引用：** §3.5.5（无 `animate-spin`，SkeletonRow 用脉冲；EmptyState/ErrorState 不带 motion）、§3.5.6（禁多层 shadow、禁 glassmorphism）、§3.5.1（直角为主，使用 `rounded-md` 即 0.3rem）。

- [ ] **Step 1：`src/components/feedback/skeleton-row.tsx`**

```tsx
import { Skeleton } from "@/components/ui/skeleton";

interface SkeletonRowProps {
  columns?: number;
  rows?: number;
}

export function SkeletonRow({ columns = 8, rows = 10 }: SkeletonRowProps) {
  return (
    <>
      {Array.from({ length: rows }).map((_, rIdx) => (
        <tr key={rIdx} className="border-b border-border">
          {Array.from({ length: columns }).map((_, cIdx) => (
            <td key={cIdx} className="px-3 py-2.5">
              <Skeleton className="h-4 w-full max-w-[120px]" />
            </td>
          ))}
        </tr>
      ))}
    </>
  );
}
```

- [ ] **Step 2：`src/components/feedback/empty-state.tsx`**

```tsx
import { Inbox } from "lucide-react";
import type { ReactNode } from "react";

interface EmptyStateProps {
  title?: string;
  description?: string;
  action?: ReactNode;
}

export function EmptyState({
  title = "暂无资产",
  description = "还没有登记任何资产。可以通过 CLI 登记：asset-hub asset register",
  action,
}: EmptyStateProps) {
  return (
    <div
      role="status"
      className="flex flex-col items-center justify-center gap-3 py-16 text-center"
    >
      <Inbox className="h-8 w-8 text-muted-foreground" aria-hidden />
      <div className="space-y-1">
        <p className="text-base font-medium text-foreground">{title}</p>
        <p className="text-sm text-muted-foreground">{description}</p>
      </div>
      {action ? <div className="mt-2">{action}</div> : null}
    </div>
  );
}
```

- [ ] **Step 3：`src/components/feedback/error-state.tsx`**

```tsx
import { AlertTriangle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { toFriendlyMessage } from "@/lib/error";

interface ErrorStateProps {
  error: unknown;
  onRetry?: () => void;
}

export function ErrorState({ error, onRetry }: ErrorStateProps) {
  return (
    <div
      role="alert"
      className="flex flex-col items-center justify-center gap-3 py-16 text-center"
    >
      <AlertTriangle className="h-8 w-8 text-destructive" aria-hidden />
      <div className="space-y-1">
        <p className="text-base font-medium text-foreground">请求失败</p>
        <p className="text-sm text-muted-foreground">{toFriendlyMessage(error)}</p>
      </div>
      {onRetry ? (
        <Button variant="outline" size="sm" onClick={onRetry} className="mt-2">
          重试
        </Button>
      ) : null}
    </div>
  );
}
```

- [ ] **Step 4：`src/components/feedback/error-boundary.tsx`**

```tsx
import { Component, type ErrorInfo, type ReactNode } from "react";
import { Button } from "@/components/ui/button";

interface Props {
  children: ReactNode;
}
interface State {
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    if (import.meta.env.DEV) {
      console.error("[ErrorBoundary]", error, info);
    }
  }

  handleReload = () => {
    window.location.reload();
  };

  render() {
    if (!this.state.error) return this.props.children;

    return (
      <div className="mx-auto flex max-w-md flex-col items-center gap-3 py-24 text-center">
        <p className="text-lg font-semibold">出错了</p>
        <p className="text-sm text-muted-foreground">
          {this.state.error.message || "未知异常"}
        </p>
        {import.meta.env.DEV && this.state.error.stack ? (
          <pre className="max-h-48 w-full overflow-auto rounded-md border border-border bg-muted p-3 text-left text-xs text-muted-foreground">
            {this.state.error.stack}
          </pre>
        ) : null}
        <Button variant="outline" size="sm" onClick={this.handleReload}>
          刷新页面
        </Button>
      </div>
    );
  }
}
```

- [ ] **Step 5：验证 build**

```bash
pnpm --dir frontend build
```

Expected：PASS。

- [ ] **Step 6：commit**

```bash
git add frontend/src/components/feedback/
git commit -m "feat(frontend): feedback 组件——ErrorBoundary / EmptyState / ErrorState / SkeletonRow"
```

---

## Task 11: status-labels + StatusBadge

**Files:**
- Create: `frontend/src/features/assets/status-labels.ts`
- Create: `frontend/src/components/status/status-badge.tsx`

**§3.5 约束引用：** §3.5.5（状态色变 transition-colors 150ms，是 Motion 三时刻之一）、§3.5.4（状态色已在 globals.css 确保与 Primary/CTA 不撞色相）、§3.5.7（本组件**不**复用 shadcn `Badge`，独立成 `StatusBadge`，避免 Badge variant 被污染）。

- [ ] **Step 1：`src/features/assets/status-labels.ts`**

```ts
import { Circle, CircleDot, MinusCircle, Wrench, type LucideIcon } from "lucide-react";

export type AssetStatus = "IN_USE" | "IDLE" | "MAINTENANCE" | "RETIRED";

export interface StatusMeta {
  label: string;
  bgVar: string; // CSS var name
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
    label: "维护",
    bgVar: "--status-maintenance",
    fgVar: "--status-maintenance-fg",
    Icon: Wrench,
  },
  RETIRED: {
    label: "报废",
    bgVar: "--status-retired",
    fgVar: "--status-retired-fg",
    Icon: MinusCircle,
  },
};
```

- [ ] **Step 2：`src/components/status/status-badge.tsx`**

```tsx
import type { CSSProperties } from "react";
import { STATUS_META, type AssetStatus } from "@/features/assets/status-labels";

interface StatusBadgeProps {
  status: AssetStatus;
}

export function StatusBadge({ status }: StatusBadgeProps) {
  const meta = STATUS_META[status];
  const style: CSSProperties = {
    backgroundColor: `var(${meta.bgVar})`,
    color: `var(${meta.fgVar})`,
  };
  return (
    <span
      className="inline-flex items-center gap-1 rounded-sm px-2 py-0.5 text-xs font-medium transition-colors duration-150"
      style={style}
    >
      <meta.Icon className="h-3 w-3" aria-hidden />
      <span>{meta.label}</span>
    </span>
  );
}
```

- [ ] **Step 3：验证 build**

```bash
pnpm --dir frontend build
```

Expected：PASS。

- [ ] **Step 4：commit**

```bash
git add frontend/src/features/assets/status-labels.ts frontend/src/components/status/status-badge.tsx
git commit -m "feat(frontend): StatusBadge + STATUS_META（Lucide 图标，transition-colors 150ms）"
```

---

## Task 12: shadcn variant 审查 + 色值重调（§3.5.7 兑现）

**Files:**
- Modify: `frontend/src/components/ui/button.tsx`
- Modify: `frontend/src/components/ui/input.tsx`
- Modify: `frontend/src/components/ui/select.tsx`
- Modify: `frontend/src/components/ui/dropdown-menu.tsx`
- Modify: `frontend/src/components/ui/badge.tsx`

**§3.5 约束引用：** §3.5.7（每个首次 add 的组件必须同 PR 完成 variant 审查）、§3.5.4（dominant+accent 结构）、§3.5.2（focus ring 显眼方块——由 globals.css 的 `*:focus-visible` 统一处理，本 Task 只需确保组件不覆盖该规则）、§3.5.5（禁 hover `transform: scale`）。

- [ ] **Step 0：快速扫描已 scaffold 组件里的 `transform: scale` 蛛丝马迹**

```bash
grep -rn "scale-\|transform:\s*scale\|active:scale" frontend/src/components/ui/ || echo "✓ no scale transforms"
```

Expected：空（或 `✓ no scale transforms`）。如有匹配，逐处删除或替换为色变。

```bash
grep -rn "transition-transform\|animate-spin" frontend/src/components/ui/ || echo "✓ no transform transitions / no spinners"
```

Expected：空。有匹配则删。

- [ ] **Step 1：Button variant 审查**

打开 `frontend/src/components/ui/button.tsx`，核查 `cva` 的 `variants` 配置：
- `default`：用 `bg-primary text-primary-foreground hover:bg-primary/90` ——符合要求
- `outline`：`border bg-background hover:bg-accent hover:text-accent-foreground` ——符合要求
- `ghost`：`hover:bg-accent hover:text-accent-foreground` ——符合要求
- `destructive`：`bg-destructive text-destructive-foreground` ——符合要求

**必须修正的**：
- 如果文件中出现任何 `transform:` 或 `scale-` 或 `active:scale-` class，删掉（§3.5.5）
- 如果 `focus-visible:ring-*` class 和 `*:focus-visible` 冲突，删掉组件级的 ring 让 globals.css 兜底

对 Button 特殊新增：如果后续需要 CTA 变体（amber），**本 Task 不加**；§3.5.4 "CTA 仅用于真正的关键动作"，M2c-1 无此需求。

- [ ] **Step 2：Input / Select 审查**

- 确保 Input 的 `focus-visible:` 规则不覆盖 globals 的 `*:focus-visible`
- 如 `rounded-md` 类残留，保留（globals 的 `--radius` 已 0.375rem，`rounded-md` 会解析为 `calc(0.375 * 0.8)` ≈ 0.3rem，符合 §3.5.1）
- 删除任何 `transition-transform` / `scale-` / `animate-*` 用法（spinner 除外，本次无）

- [ ] **Step 3：DropdownMenu / Select trigger 审查**

- hover 背景用 `accent` 色温（已是默认）
- 删除 transform scale 用法

- [ ] **Step 4：Badge 审查**

- `Badge` 仅用作"通用标签"（资产类型等），**不**作为 `StatusBadge` 的 wrapper
- variant 保持默认

- [ ] **Step 5：验证 build + lint**

```bash
pnpm --dir frontend build && pnpm --dir frontend lint
```

Expected：PASS。

- [ ] **Step 6：commit**

```bash
git add frontend/src/components/ui/
git commit -m "refactor(frontend): shadcn 组件 variant 审查，移除 transform-scale 等反纲领细节"
```

---

## Task 13: AppLayout + main.tsx 布线 + __root.tsx 接入

**Files:**
- Create: `frontend/src/components/layout/app-layout.tsx`
- Modify: `frontend/src/main.tsx`
- Modify: `frontend/src/routes/__root.tsx`

**§3.5 约束引用：** D7（品牌字"小组资产管理工具"）、§3.5.1（header 几何克制：无大圆角、无渐变、无阴影堆叠）、§3.5.6（header 用 1px `border-b`，不用 shadow）。

- [ ] **Step 1：`src/components/layout/app-layout.tsx`**

```tsx
import { Outlet } from "@tanstack/react-router";
import { Toaster } from "sonner";
import { ThemeToggle } from "@/components/theme/theme-toggle";
import { ErrorBoundary } from "@/components/feedback/error-boundary";

export function AppLayout() {
  return (
    <div className="min-h-screen bg-background text-foreground">
      <header className="border-b border-border">
        <div className="mx-auto flex h-14 max-w-[1400px] items-center justify-between px-6">
          <div className="flex items-center gap-3">
            <span className="text-sm font-medium tracking-tight text-foreground">
              小组资产管理工具
            </span>
          </div>
          <div className="flex items-center gap-2">
            <ThemeToggle />
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-[1400px] px-6 py-6">
        <ErrorBoundary>
          <Outlet />
        </ErrorBoundary>
      </main>
      <Toaster position="top-right" richColors />
    </div>
  );
}
```

- [ ] **Step 2：改 `src/routes/__root.tsx`**

```tsx
import { createRootRoute } from "@tanstack/react-router";
import { AppLayout } from "@/components/layout/app-layout";

export const Route = createRootRoute({
  component: AppLayout,
});
```

如果本里程碑希望看到 Devtools（推荐，开发友好），改用：

```tsx
import { createRootRoute } from "@tanstack/react-router";
import { TanStackRouterDevtools } from "@tanstack/react-router-devtools";
import { ReactQueryDevtools } from "@tanstack/react-query-devtools";
import { AppLayout } from "@/components/layout/app-layout";

function RootWithDevtools() {
  return (
    <>
      <AppLayout />
      {import.meta.env.DEV && (
        <>
          <TanStackRouterDevtools />
          <ReactQueryDevtools initialIsOpen={false} />
        </>
      )}
    </>
  );
}

export const Route = createRootRoute({
  component: RootWithDevtools,
});
```

> Router Devtools 需要装：`pnpm --dir frontend add -D @tanstack/react-router-devtools`。若不想引入，先用上一版本（不带 Devtools），后续 Task 里集中加。

**本 Task 选择**：引入 Router + Query Devtools，装包：

```bash
pnpm --dir frontend add -D @tanstack/react-router-devtools
```

- [ ] **Step 3：改 `src/main.tsx`**

```tsx
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { RouterProvider, createRouter } from "@tanstack/react-router";
import { QueryClientProvider } from "@tanstack/react-query";
import { queryClient } from "@/api/query-client";
import { ThemeProvider } from "@/components/theme/theme-provider";
import { routeTree } from "./routeTree.gen";
import "./styles/globals.css";

const router = createRouter({ routeTree });

declare module "@tanstack/react-router" {
  interface Register {
    router: typeof router;
  }
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>
        <RouterProvider router={router} />
      </ThemeProvider>
    </QueryClientProvider>
  </StrictMode>,
);
```

- [ ] **Step 4：验证 build + 启动 dev server 肉眼核查**

```bash
pnpm --dir frontend build
pnpm --dir frontend dev
```

打开 `http://localhost:5173`：
- ✓ 标题栏显示"**小组资产管理工具**"
- ✓ 浏览器 tab 标题显示"**小组资产管理工具**"
- ✓ 右上角有 ThemeToggle，点击能切 Light/Dark/System
- ✓ 切 Dark 后刷新，**不闪白**（防闪烁脚本生效）
- ✓ 切换时 header 背景、字色平滑变化（transition-colors 已在 shadcn 组件里）
- ✓ Router Devtools（底部）可见

关 dev server。

- [ ] **Step 5：commit**

```bash
git add frontend/src/components/layout/ frontend/src/routes/__root.tsx frontend/src/main.tsx frontend/package.json frontend/pnpm-lock.yaml
git commit -m "feat(frontend): AppLayout + main.tsx 布线（QueryClientProvider + ThemeProvider + Devtools）"
```

---

## Task 14: search-schema + routes/index.tsx 薄壳（三态占位）

**Files:**
- Create: `frontend/src/features/assets/list/search-schema.ts`
- Modify: `frontend/src/api/query-keys.ts`（把 `AssetListParams` 换成 `AssetsSearch`）
- Modify: `frontend/src/api/hooks/assets.ts`（import 真实 `AssetsSearch`）
- Modify: `frontend/src/routes/index.tsx`

**§3.5 约束引用：** §3.5.6（EmptyState 不用 shadow 堆叠；骨架期间用 SkeletonRow）、§3.5.5（本 Task 仅装载，还未启用 stagger 动画，Task 17 才加）。

- [ ] **Step 1：`src/features/assets/list/search-schema.ts`**

```ts
import { z } from "zod";

export const ASSET_STATUS_VALUES = ["IN_USE", "IDLE", "MAINTENANCE", "RETIRED"] as const;

export const assetsSearchSchema = z.object({
  type: z.string().uuid().optional(),
  status: z.enum(ASSET_STATUS_VALUES).optional(),
  holder: z.string().optional(),
  q: z.string().optional(),
  sort: z.string().optional(),
  page: z.coerce.number().int().min(1).default(1),
  pageSize: z.coerce.number().int().min(10).max(200).default(50),
});

export type AssetsSearch = z.infer<typeof assetsSearchSchema>;
```

- [ ] **Step 2：改 `src/api/query-keys.ts`（把 `AssetListParams` 换成真实类型）**

```ts
import type { AssetsSearch } from "@/features/assets/list/search-schema";

export const qk = {
  assets: {
    all: ["assets"] as const,
    list: (params: AssetsSearch) => ["assets", "list", params] as const,
    detail: (id: string) => ["assets", "detail", id] as const,
  },
  assetTypes: {
    all: ["assetTypes"] as const,
    list: () => ["assetTypes", "list"] as const,
  },
} as const;
```

- [ ] **Step 3：改 `src/api/hooks/assets.ts`（移除 Task 6 的临时 `AssetsSearch` 类型，import 真的）**

在文件顶端把：

```ts
// TEMPORARY: will be replaced in Task 14 after search-schema.ts exists
type AssetsSearch = { ... };
```

换成：

```ts
import type { AssetsSearch } from "@/features/assets/list/search-schema";
```

保留下方所有函数不动。

- [ ] **Step 4：改 `src/routes/index.tsx`（薄壳，三态派发）**

```tsx
import { createFileRoute } from "@tanstack/react-router";
import { useAssetsQuery } from "@/api/hooks/assets";
import { EmptyState } from "@/components/feedback/empty-state";
import { ErrorState } from "@/components/feedback/error-state";
import { SkeletonRow } from "@/components/feedback/skeleton-row";
import { assetsSearchSchema } from "@/features/assets/list/search-schema";

export const Route = createFileRoute("/")({
  validateSearch: (search) => assetsSearchSchema.parse(search),
  component: AssetListPage,
});

function AssetListPage() {
  const search = Route.useSearch();
  const query = useAssetsQuery(search);

  if (query.isLoading) {
    return (
      <section>
        <h2 className="sr-only">资产列表</h2>
        <table className="w-full">
          <tbody>
            <SkeletonRow columns={8} rows={search.pageSize} />
          </tbody>
        </table>
      </section>
    );
  }

  if (query.isError) {
    return <ErrorState error={query.error} onRetry={() => query.refetch()} />;
  }

  if (!query.data || query.data.length === 0) {
    return <EmptyState />;
  }

  return (
    <section>
      <h2 className="text-lg font-medium">资产列表（骨架）</h2>
      <p className="mt-1 text-sm text-muted-foreground">
        共 {query.data.length} 条 —— 表格与筛选将在后续 Task 接入
      </p>
    </section>
  );
}
```

- [ ] **Step 5：验证 build + dev 核查**

```bash
pnpm --dir frontend build
pnpm --dir frontend dev
```

打开 `http://localhost:5173`，根据数据库状态应看到：
- 空库：`EmptyState` 居中显示"暂无资产"
- 有数据：`资产列表（骨架） · 共 N 条` 文案
- 后端挂掉：`ErrorState` + 重试按钮

关 dev server。

- [ ] **Step 6：commit**

```bash
git add frontend/src/features/assets/list/search-schema.ts \
        frontend/src/api/query-keys.ts frontend/src/api/hooks/assets.ts \
        frontend/src/routes/index.tsx
git commit -m "feat(frontend): search-schema（Zod）+ AssetListPage 三态薄壳"
```

---

## Task 15: AssetsFilters

**Files:**
- Create: `frontend/src/features/assets/list/assets-filters.tsx`
- Modify: `frontend/src/routes/index.tsx`（挂 Filters）

**§3.5 约束引用：** §3.5.2（focus-visible 方块由 globals.css 承担，Input/Select 不覆盖）、§3.5.4（按钮只用 secondary/outline，不用 CTA amber）、§3.5.5（改筛选不触发整页动画，仅 tbody 淡切——见 Task 17；本 Task 无自己的动画）、§3.5.1（几何克制：Filters 栏无大圆角、无背景渐变）。

- [ ] **Step 1：`src/features/assets/list/assets-filters.tsx`**

```tsx
import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "@tanstack/react-router";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useAssetTypesQuery } from "@/api/hooks/types";
import {
  ASSET_STATUS_VALUES,
  type AssetsSearch,
} from "@/features/assets/list/search-schema";
import { STATUS_META } from "@/features/assets/status-labels";
import { debounce } from "@/lib/debounce";

type NavigateFn = ReturnType<typeof useNavigate>;

interface AssetsFiltersProps {
  search: AssetsSearch;
}

const ALL = "__ALL__";

export function AssetsFilters({ search }: AssetsFiltersProps) {
  const navigate = useNavigate({ from: "/" });
  const typesQuery = useAssetTypesQuery();

  // q 用本地 state + 300ms debounce 写 URL
  const [qLocal, setQLocal] = useState(search.q ?? "");
  useEffect(() => setQLocal(search.q ?? ""), [search.q]);

  const pushQ = useMemo(
    () =>
      debounce((value: string) => {
        navigate({
          search: (prev) => ({ ...prev, q: value || undefined, page: 1 }),
        });
      }, 300),
    [navigate],
  );

  const onQChange = (value: string) => {
    setQLocal(value);
    pushQ(value);
  };

  const onSelectChange = (key: keyof AssetsSearch) => (value: string) => {
    navigate({
      search: (prev) => ({
        ...prev,
        [key]: value === ALL ? undefined : value,
        page: 1,
      }),
    });
  };

  const onHolderCommit = (value: string) => {
    navigate({
      search: (prev) => ({ ...prev, holder: value || undefined, page: 1 }),
    });
  };

  const onReset = () => {
    navigate({
      search: () => ({ page: 1, pageSize: search.pageSize }) as AssetsSearch,
    });
    setQLocal("");
  };

  return (
    <div className="flex flex-wrap items-center gap-3">
      <Input
        value={qLocal}
        onChange={(e) => onQChange(e.target.value)}
        placeholder="关键词（名称 / 编号 / 备注）"
        className="w-64"
        aria-label="关键词搜索"
      />

      <Select
        value={search.type ?? ALL}
        onValueChange={onSelectChange("type")}
      >
        <SelectTrigger className="w-40" aria-label="类型筛选">
          <SelectValue placeholder="类型" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value={ALL}>全部类型</SelectItem>
          {typesQuery.data?.map((t: { id: string; name: string }) => (
            <SelectItem key={t.id} value={t.id}>
              {t.name}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      <Select
        value={search.status ?? ALL}
        onValueChange={onSelectChange("status")}
      >
        <SelectTrigger className="w-32" aria-label="状态筛选">
          <SelectValue placeholder="状态" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value={ALL}>全部状态</SelectItem>
          {ASSET_STATUS_VALUES.map((s) => (
            <SelectItem key={s} value={s}>
              {STATUS_META[s].label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      <HolderInput
        initial={search.holder ?? ""}
        onCommit={onHolderCommit}
        navigate={navigate}
      />

      <Button variant="outline" size="sm" onClick={onReset}>
        重置
      </Button>
    </div>
  );
}

function HolderInput({
  initial,
  onCommit,
  navigate: _navigate,
}: {
  initial: string;
  onCommit: (value: string) => void;
  navigate: NavigateFn;
}) {
  const [v, setV] = useState(initial);
  const lastCommittedRef = useRef(initial);

  useEffect(() => {
    setV(initial);
    lastCommittedRef.current = initial;
  }, [initial]);

  const commit = () => {
    if (v === lastCommittedRef.current) return;
    lastCommittedRef.current = v;
    onCommit(v);
  };

  return (
    <Input
      value={v}
      onChange={(e) => setV(e.target.value)}
      onBlur={commit}
      onKeyDown={(e) => {
        if (e.key === "Enter") {
          e.currentTarget.blur();
        }
      }}
      placeholder="保管人"
      className="w-40"
      aria-label="保管人筛选"
    />
  );
}
```

> 如果 `useAssetTypesQuery` 返回的字段不是 `{id, name}`（取决于 `AssetTypeRead` DTO），请改 item 的字段读取。

- [ ] **Step 2：挂到 `src/routes/index.tsx`**

```tsx
import { createFileRoute } from "@tanstack/react-router";
import { useAssetsQuery } from "@/api/hooks/assets";
import { EmptyState } from "@/components/feedback/empty-state";
import { ErrorState } from "@/components/feedback/error-state";
import { SkeletonRow } from "@/components/feedback/skeleton-row";
import { AssetsFilters } from "@/features/assets/list/assets-filters";
import { assetsSearchSchema } from "@/features/assets/list/search-schema";

export const Route = createFileRoute("/")({
  validateSearch: (search) => assetsSearchSchema.parse(search),
  component: AssetListPage,
});

function AssetListPage() {
  const search = Route.useSearch();
  const query = useAssetsQuery(search);

  return (
    <section className="space-y-4">
      <AssetsFilters search={search} />
      {renderBody()}
    </section>
  );

  function renderBody() {
    if (query.isLoading) {
      return (
        <table className="w-full">
          <tbody>
            <SkeletonRow columns={8} rows={search.pageSize} />
          </tbody>
        </table>
      );
    }
    if (query.isError) {
      return <ErrorState error={query.error} onRetry={() => query.refetch()} />;
    }
    if (!query.data || query.data.length === 0) {
      return <EmptyState />;
    }
    return (
      <p className="text-sm text-muted-foreground">
        共 {query.data.length} 条 —— 表格将在 Task 17 接入
      </p>
    );
  }
}
```

- [ ] **Step 3：验证 build + dev 核查**

```bash
pnpm --dir frontend build
pnpm --dir frontend dev
```

测 URL 同步：
- 改类型下拉 → URL 出现 `?type=<uuid>`
- 改状态下拉 → URL 追加 `&status=IDLE`
- 关键词输入 → 停 300ms 后 URL 出现 `&q=xxx`
- 保管人输入后 blur → URL 追加 `&holder=xxx`
- 点"重置" → URL 清空到 `?pageSize=50&page=1`

关 dev server。

- [ ] **Step 4：commit**

```bash
git add frontend/src/features/assets/list/assets-filters.tsx frontend/src/routes/index.tsx
git commit -m "feat(frontend): AssetsFilters（URL-sync + q 防抖 300ms + holder blur-commit）"
```

---

## Task 16: ColumnVisibility

**Files:**
- Create: `frontend/src/features/assets/list/column-visibility.tsx`

**§3.5 约束引用：** §3.5.7（用已在 Task 12 审过的 DropdownMenu）、§3.5.5（checkbox 切换无 transform 动画）。

- [ ] **Step 1：`src/features/assets/list/column-visibility.tsx`**

```tsx
import { useEffect, useState } from "react";
import { Settings2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuCheckboxItem,
  DropdownMenuContent,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

export type ColumnKey =
  | "asset_code"
  | "name"
  | "type"
  | "status"
  | "holder"
  | "location"
  | "updated_at";

export const COLUMN_LABELS: Record<ColumnKey, string> = {
  asset_code: "编号",
  name: "名称",
  type: "类型",
  status: "状态",
  holder: "保管人",
  location: "位置",
  updated_at: "更新时间",
};

const STORAGE_KEY = "asset-hub.list.columns";
const ALL_KEYS: ColumnKey[] = [
  "asset_code",
  "name",
  "type",
  "status",
  "holder",
  "location",
  "updated_at",
];

export function useColumnVisibility() {
  const [visible, setVisible] = useState<Record<ColumnKey, boolean>>(() => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw) {
        const parsed = JSON.parse(raw) as Partial<Record<ColumnKey, boolean>>;
        return Object.fromEntries(
          ALL_KEYS.map((k) => [k, parsed[k] !== false]),
        ) as Record<ColumnKey, boolean>;
      }
    } catch {
      // fall through to default
    }
    return Object.fromEntries(ALL_KEYS.map((k) => [k, true])) as Record<
      ColumnKey,
      boolean
    >;
  });

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(visible));
  }, [visible]);

  const toggle = (key: ColumnKey) =>
    setVisible((v) => ({ ...v, [key]: !v[key] }));

  return { visible, toggle };
}

interface ColumnVisibilityMenuProps {
  visible: Record<ColumnKey, boolean>;
  onToggle: (key: ColumnKey) => void;
}

export function ColumnVisibilityMenu({ visible, onToggle }: ColumnVisibilityMenuProps) {
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="outline" size="sm" aria-label="列显隐">
          <Settings2 className="mr-2 h-4 w-4" />
          <span>列显隐</span>
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        <DropdownMenuLabel>显示列</DropdownMenuLabel>
        <DropdownMenuSeparator />
        {ALL_KEYS.map((key) => (
          <DropdownMenuCheckboxItem
            key={key}
            checked={visible[key]}
            onCheckedChange={() => onToggle(key)}
            onSelect={(e) => e.preventDefault()} // 避免点一项就关菜单
          >
            {COLUMN_LABELS[key]}
          </DropdownMenuCheckboxItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
```

> 如 shadcn 的 `dropdown-menu` 未导出 `DropdownMenuCheckboxItem`，手动补导出或在组件内用：`<DropdownMenuCheckboxItem>` 可能来自 `@radix-ui/react-dropdown-menu`。确认 `components/ui/dropdown-menu.tsx` 有 `DropdownMenuCheckboxItem` export；若无，**补一条 export**（shadcn 的标准 dropdown-menu 脚手一般带 Checkbox 变体，版本差异时补上即可）。

- [ ] **Step 2：验证 build**

```bash
pnpm --dir frontend build
```

Expected：PASS。若 `DropdownMenuCheckboxItem` 报不存在，打开 `frontend/src/components/ui/dropdown-menu.tsx`，添加：

```tsx
import { CheckboxItem as DropdownMenuCheckboxItem } from "@radix-ui/react-dropdown-menu";
// ...然后 export { DropdownMenuCheckboxItem };
```

（具体 import 路径以生成的 dropdown-menu.tsx 为准。）

- [ ] **Step 3：commit**

```bash
git add frontend/src/features/assets/list/column-visibility.tsx frontend/src/components/ui/dropdown-menu.tsx
git commit -m "feat(frontend): ColumnVisibility 菜单 + useColumnVisibility（localStorage 持久化）"
```

---

## Task 17: AssetsTable（TanStack Table + stagger reveal + 筛选淡切 + 行为）

**Files:**
- Create: `frontend/src/features/assets/list/assets-table.tsx`

**§3.5 约束引用：** §3.5.1（直角、无装饰渐变）、§3.5.2（`asset_code` 用 `font-code` 等宽；表头显眼 focus ring 由 globals 继承；数字 `tnum` 已全局生效）、§3.5.5 时刻 1（首屏 stagger reveal）、§3.5.5 时刻 2（筛选变更 tbody 淡切）、§3.5.6（hover 行用背景色温变化，不用 shadow）、§3.5.7（⋯ 下拉用已审的 DropdownMenu）。

- [ ] **Step 1：`src/features/assets/list/assets-table.tsx`**

```tsx
import { useMemo } from "react";
import { useNavigate } from "@tanstack/react-router";
import {
  type ColumnDef,
  flexRender,
  getCoreRowModel,
  getPaginationRowModel,
  getSortedRowModel,
  type SortingState,
  useReactTable,
} from "@tanstack/react-table";
import { MoreHorizontal } from "lucide-react";
import { ArrowDown, ArrowUp, ArrowUpDown } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { StatusBadge } from "@/components/status/status-badge";
import type { AssetStatus } from "@/features/assets/status-labels";
import type { AssetsSearch } from "@/features/assets/list/search-schema";
import {
  COLUMN_LABELS,
  type ColumnKey,
} from "@/features/assets/list/column-visibility";

interface AssetRow {
  id: string;
  asset_code: string;
  serial_number?: string | null;
  name: string;
  type_id?: string | null;
  type_name?: string | null;
  status: AssetStatus;
  holder?: string | null;
  location?: string | null;
  updated_at: string;
}

interface AssetsTableProps {
  rows: AssetRow[];
  search: AssetsSearch;
  visible: Record<ColumnKey, boolean>;
  /** 筛选 / 排序 / 翻页变更时由父组件递增，用于触发 tbody 淡切（§3.5.5 时刻 2） */
  bodyKey: string;
}

/** 把 URL sort（"asset_code" / "-updated_at"）↔ TanStack sorting state 相互翻译。 */
function urlSortToState(sort?: string): SortingState {
  if (!sort) return [];
  return sort.startsWith("-")
    ? [{ id: sort.slice(1), desc: true }]
    : [{ id: sort, desc: false }];
}
function stateToUrlSort(state: SortingState): string | undefined {
  if (state.length === 0) return undefined;
  const s = state[0];
  return s.desc ? `-${s.id}` : s.id;
}

export function AssetsTable({
  rows,
  search,
  visible,
  bodyKey,
}: AssetsTableProps) {
  const navigate = useNavigate({ from: "/" });

  const sorting = useMemo(() => urlSortToState(search.sort), [search.sort]);

  const columns = useMemo<ColumnDef<AssetRow>[]>(
    () => [
      {
        id: "asset_code",
        accessorKey: "asset_code",
        header: COLUMN_LABELS.asset_code,
        cell: ({ row }) => (
          <span className="font-code text-xs">{row.original.asset_code}</span>
        ),
      },
      {
        id: "name",
        accessorKey: "name",
        header: COLUMN_LABELS.name,
        cell: ({ row }) => (
          <span className="font-medium">{row.original.name}</span>
        ),
      },
      {
        id: "type",
        accessorKey: "type_name",
        header: COLUMN_LABELS.type,
        enableSorting: false,
        cell: ({ row }) => (
          <span className="text-sm text-muted-foreground">
            {row.original.type_name ?? "—"}
          </span>
        ),
      },
      {
        id: "status",
        accessorKey: "status",
        header: COLUMN_LABELS.status,
        enableSorting: false,
        cell: ({ row }) => <StatusBadge status={row.original.status} />,
      },
      {
        id: "holder",
        accessorKey: "holder",
        header: COLUMN_LABELS.holder,
        cell: ({ row }) => row.original.holder ?? "—",
      },
      {
        id: "location",
        accessorKey: "location",
        header: COLUMN_LABELS.location,
        cell: ({ row }) => row.original.location ?? "—",
      },
      {
        id: "updated_at",
        accessorKey: "updated_at",
        header: COLUMN_LABELS.updated_at,
        cell: ({ row }) =>
          new Date(row.original.updated_at).toLocaleString("zh-CN"),
      },
      {
        id: "actions",
        header: "",
        enableSorting: false,
        cell: ({ row }) => (
          <RowActions id={row.original.id} />
        ),
      },
    ],
    [],
  );

  const columnVisibility = useMemo(
    () => ({
      asset_code: visible.asset_code,
      name: visible.name,
      type: visible.type,
      status: visible.status,
      holder: visible.holder,
      location: visible.location,
      updated_at: visible.updated_at,
      actions: true,
    }),
    [visible],
  );

  const table = useReactTable({
    data: rows,
    columns,
    state: {
      sorting,
      columnVisibility,
      pagination: {
        pageIndex: search.page - 1,
        pageSize: search.pageSize,
      },
    },
    manualPagination: false,
    manualSorting: false,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    onSortingChange: (updater) => {
      const next = typeof updater === "function" ? updater(sorting) : updater;
      navigate({
        search: (prev) => ({
          ...prev,
          sort: stateToUrlSort(next),
          page: 1,
        }),
      });
    },
  });

  return (
    <div className="overflow-x-auto rounded-sm border border-border">
      <table className="w-full text-sm">
        <thead>
          {table.getHeaderGroups().map((hg) => (
            <tr key={hg.id} className="border-b border-border bg-muted/40 text-left">
              {hg.headers.map((header) => {
                const canSort = header.column.getCanSort();
                const sortDir = header.column.getIsSorted();
                return (
                  <th
                    key={header.id}
                    className="px-3 py-2 text-xs font-medium uppercase tracking-wide text-muted-foreground"
                  >
                    {canSort ? (
                      <button
                        type="button"
                        className="inline-flex items-center gap-1 hover:text-foreground"
                        onClick={header.column.getToggleSortingHandler()}
                      >
                        {flexRender(header.column.columnDef.header, header.getContext())}
                        {sortDir === "asc" ? (
                          <ArrowUp className="h-3 w-3" aria-hidden />
                        ) : sortDir === "desc" ? (
                          <ArrowDown className="h-3 w-3" aria-hidden />
                        ) : (
                          <ArrowUpDown className="h-3 w-3 opacity-50" aria-hidden />
                        )}
                      </button>
                    ) : (
                      flexRender(header.column.columnDef.header, header.getContext())
                    )}
                  </th>
                );
              })}
            </tr>
          ))}
        </thead>
        {/* bodyKey 变化 → React 认为是新 tbody，class tbody-fade 重新触发动画（§3.5.5 时刻 2） */}
        <tbody key={bodyKey} className="tbody-fade">
          {table.getRowModel().rows.map((row, idx) => (
            <tr
              key={row.id}
              className="stagger-row cursor-pointer border-b border-border transition-colors hover:bg-accent/40"
              style={{ animationDelay: idx < 20 ? `${idx * 18}ms` : "0ms" }}
              onClick={() => navigate({ to: "/assets/$id", params: { id: row.original.id } })}
            >
              {row.getVisibleCells().map((cell) => (
                <td
                  key={cell.id}
                  className="px-3 py-2 align-middle"
                  onClick={(e) => {
                    // ⋯ 单元格阻止行点击冒泡
                    if (cell.column.id === "actions") e.stopPropagation();
                  }}
                >
                  {flexRender(cell.column.columnDef.cell, cell.getContext())}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function RowActions({ id: _id }: { id: string }) {
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="icon" aria-label="更多操作">
          <MoreHorizontal className="h-4 w-4" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        <DropdownMenuItem disabled>编辑（M2c-3 开放）</DropdownMenuItem>
        <DropdownMenuItem disabled>派发（M2c-2 开放）</DropdownMenuItem>
        <DropdownMenuItem disabled>归还（M2c-2 开放）</DropdownMenuItem>
        <DropdownMenuItem disabled>删除（M2c-3 开放）</DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
```

> `navigate({ to: "/assets/$id" })` 会在 TanStack Router 的 typed routes 报错（目前没有 `/assets/$id` 路由）。**本里程碑暂时用字符串路径 + 忽略类型**：

```ts
navigate({ to: `/assets/${row.original.id}` as "/" });
```

或创建占位路由 `frontend/src/routes/assets.$id.tsx`：

```tsx
import { createFileRoute } from "@tanstack/react-router";
export const Route = createFileRoute("/assets/$id")({
  component: () => (
    <div className="py-12 text-center text-muted-foreground">
      资产详情 —— M2c-2 开放
    </div>
  ),
});
```

**推荐选后者**（加占位路由文件），否则 navigate 会 404 到 Router 默认 `notFoundComponent`，也能接受。**Task 17 选用：创建占位路由文件**（见下一步）。

- [ ] **Step 2：创建详情占位路由**

创建 `frontend/src/routes/assets.$id.tsx`：

```tsx
import { createFileRoute } from "@tanstack/react-router";

export const Route = createFileRoute("/assets/$id")({
  component: PlaceholderPage,
});

function PlaceholderPage() {
  return (
    <div className="py-12 text-center text-sm text-muted-foreground">
      资产详情 —— 将在 M2c-2 开放
    </div>
  );
}
```

再把 `assets-table.tsx` 里的行点击改成：

```ts
onClick={() => navigate({ to: "/assets/$id", params: { id: row.original.id } })}
```

- [ ] **Step 3：验证 build + dev 核查**

```bash
pnpm --dir frontend build
pnpm --dir frontend dev
```

打开 `http://localhost:5173`，若后端已 seed 几条资产：
- ✓ 表格渲染，前 20 行明显从下向上 stagger 淡入（约 400ms 内完成）
- ✓ 切筛选：tbody 整体有 120-160ms 的 opacity + translateY 过渡
- ✓ 点表头（`asset_code` / `name` / `holder` / `location` / `updated_at`）依次切升序/降序/无序
- ✓ 点行 → 跳到 `/assets/<uuid>` 显示"资产详情 —— 将在 M2c-2 开放"
- ✓ 点 ⋯ 下拉四项 disabled + 说明文字可见
- ✓ Chrome DevTools: "Prefers reduced motion" toggle 开启 → stagger/淡切全部变成即显

关 dev server。

- [ ] **Step 4：commit**

```bash
git add frontend/src/features/assets/list/assets-table.tsx frontend/src/routes/assets.\$id.tsx
git commit -m "feat(frontend): AssetsTable（TanStack Table + stagger reveal + 筛选淡切 + 行为占位）"
```

---

## Task 18: AssetsPagination

**Files:**
- Create: `frontend/src/features/assets/list/assets-pagination.tsx`

**§3.5 约束引用：** §3.5.4（翻页按钮用 outline 变体，不用 CTA amber）、§3.5.2（数字等宽 `tnum` 已全局生效，页码字段自然对齐）、§3.5.5（翻页触发 tbody 淡切——由 Task 17 的 `bodyKey` 承担）。

- [ ] **Step 1：`src/features/assets/list/assets-pagination.tsx`**

```tsx
import { useNavigate } from "@tanstack/react-router";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { AssetsSearch } from "@/features/assets/list/search-schema";

interface AssetsPaginationProps {
  search: AssetsSearch;
  total: number;
}

const PAGE_SIZES = [20, 50, 100, 200];

export function AssetsPagination({ search, total }: AssetsPaginationProps) {
  const navigate = useNavigate({ from: "/" });

  const totalPages = Math.max(1, Math.ceil(total / search.pageSize));
  const page = Math.min(search.page, totalPages);

  const goto = (nextPage: number) =>
    navigate({
      search: (prev) => ({ ...prev, page: Math.max(1, Math.min(nextPage, totalPages)) }),
    });

  const changePageSize = (value: string) =>
    navigate({
      search: (prev) => ({ ...prev, pageSize: Number(value), page: 1 }),
    });

  return (
    <div className="flex items-center justify-between gap-4 text-sm">
      <div className="text-muted-foreground">
        共 <span className="font-code">{total}</span> 条 · 第 <span className="font-code">{page}</span> / <span className="font-code">{totalPages}</span> 页
      </div>

      <div className="flex items-center gap-2">
        <Select value={String(search.pageSize)} onValueChange={changePageSize}>
          <SelectTrigger className="w-24" aria-label="每页条数">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {PAGE_SIZES.map((n) => (
              <SelectItem key={n} value={String(n)}>
                {n} 条/页
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Button
          variant="outline"
          size="icon"
          onClick={() => goto(page - 1)}
          disabled={page <= 1}
          aria-label="上一页"
        >
          <ChevronLeft className="h-4 w-4" />
        </Button>

        <Button
          variant="outline"
          size="icon"
          onClick={() => goto(page + 1)}
          disabled={page >= totalPages}
          aria-label="下一页"
        >
          <ChevronRight className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
}
```

- [ ] **Step 2：验证 build**

```bash
pnpm --dir frontend build
```

Expected：PASS。

- [ ] **Step 3：commit**

```bash
git add frontend/src/features/assets/list/assets-pagination.tsx
git commit -m "feat(frontend): AssetsPagination（URL-synced page/pageSize + outline 变体）"
```

---

## Task 19: AssetListPage 最终组装（Filters + ColumnVisibility + Table + Pagination）

**Files:**
- Modify: `frontend/src/routes/index.tsx`

**§3.5 约束引用：** §3.5.1（布局几何克制）、§3.5.5（三态渲染下 table 才有动画；loading/error/empty 无 motion）、§3.5.6（Filters 栏与表格之间用间距不用 shadow 分层）。

- [ ] **Step 1：完整替换 `src/routes/index.tsx`**

```tsx
import { useEffect, useMemo } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { useAssetsQuery } from "@/api/hooks/assets";
import { EmptyState } from "@/components/feedback/empty-state";
import { ErrorState } from "@/components/feedback/error-state";
import { SkeletonRow } from "@/components/feedback/skeleton-row";
import { AssetsFilters } from "@/features/assets/list/assets-filters";
import { AssetsPagination } from "@/features/assets/list/assets-pagination";
import { AssetsTable } from "@/features/assets/list/assets-table";
import {
  ColumnVisibilityMenu,
  useColumnVisibility,
} from "@/features/assets/list/column-visibility";
import { assetsSearchSchema } from "@/features/assets/list/search-schema";

const WARN_THRESHOLD = 2000;

export const Route = createFileRoute("/")({
  validateSearch: (search) => assetsSearchSchema.parse(search),
  component: AssetListPage,
});

function AssetListPage() {
  const search = Route.useSearch();
  const query = useAssetsQuery(search);
  const { visible, toggle } = useColumnVisibility();

  // 2000 条告警（§7.2 数据量保险）
  useEffect(() => {
    if (query.data && query.data.length > WARN_THRESHOLD) {
      console.warn(
        `asset count ${query.data.length} exceeds client-paginate threshold (${WARN_THRESHOLD}); consider server-side pagination`,
      );
    }
  }, [query.data]);

  const bodyKey = useMemo(
    () => JSON.stringify({ s: search, v: visible }),
    [search, visible],
  );

  return (
    <section className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <AssetsFilters search={search} />
        <ColumnVisibilityMenu visible={visible} onToggle={toggle} />
      </div>

      {renderBody()}
    </section>
  );

  function renderBody() {
    if (query.isLoading) {
      return (
        <div className="overflow-x-auto rounded-sm border border-border">
          <table className="w-full">
            <tbody>
              <SkeletonRow columns={8} rows={Math.min(search.pageSize, 10)} />
            </tbody>
          </table>
        </div>
      );
    }
    if (query.isError) {
      return <ErrorState error={query.error} onRetry={() => query.refetch()} />;
    }
    if (!query.data || query.data.length === 0) {
      return <EmptyState />;
    }

    return (
      <>
        <AssetsTable
          rows={query.data as Parameters<typeof AssetsTable>[0]["rows"]}
          search={search}
          visible={visible}
          bodyKey={bodyKey}
        />
        <AssetsPagination search={search} total={query.data.length} />
      </>
    );
  }
}
```

> 如果 TS 对 `query.data` 类型报 issue，用 `as AssetRow[]`（并从 `assets-table.tsx` 导出 `AssetRow`）。

- [ ] **Step 2：从 `assets-table.tsx` 导出 `AssetRow` 类型**

打开 `frontend/src/features/assets/list/assets-table.tsx`，把 `interface AssetRow` 加 `export`：

```ts
export interface AssetRow { ... }
```

并在 `routes/index.tsx` 顶部 import：

```ts
import { AssetsTable, type AssetRow } from "@/features/assets/list/assets-table";
```

再把 `rows={query.data as Parameters<typeof AssetsTable>[0]["rows"]}` 换成 `rows={query.data as AssetRow[]}`。

- [ ] **Step 3：验证 build + 全流程 dev 核查**

```bash
pnpm --dir frontend build && pnpm --dir frontend lint
pnpm --dir frontend dev
```

走完附录 A 手工烟测清单。

- [ ] **Step 4：commit**

```bash
git add frontend/src/routes/index.tsx frontend/src/features/assets/list/assets-table.tsx
git commit -m "feat(frontend): AssetListPage 最终组装——Filters + 列显隐 + 表格 + 分页 + 三态"
```

---

## Task 20: 手工烟测 + frontend-design 合并前审查 + 纠偏回写

**Files:**
- Modify (if needed): `design-system/asset-hub/MASTER.md` / `design-system/asset-hub/pages/assets-list.md`
- Optional Modify: 任何发现问题的组件文件

**§3.5 约束引用：** §3.4 ④（实施期 3 闸门之最终合并前审查）。

- [ ] **Step 1：按 spec 附录 A 走 15 项烟测**

| # | 步骤 | 期望 |
|---|------|------|
| 1 | 清空 `data/asset_hub.db`，刷 `/` | EmptyState 显示 |
| 2 | kill 后端，刷 `/` | ErrorState + Retry；拉起后端，点 Retry 成功 |
| 3 | 依次改 type / status / q / sort / page，URL 逐步增长，复制 URL 在新 tab 打开 | 新 tab 筛选一致 |
| 4 | 应用一组筛选，浏览器刷新 | 筛选保留 |
| 5 | 翻到第 3 页再改 status | 自动回第 1 页 |
| 6 | 关掉 2 列，刷新 | 保留 |
| 7 | 切 Light / Dark / System 三次；系统切 dark 时 System 模式响应 | 每次无闪烁 |
| 8 | 关键词连续打字，DevTools Network | 只有最后一次 `/api/assets` 请求 |
| 9 | 点行 | 跳 `/assets/<uuid>` 占位页 |
| 10 | 点 ⋯ | 四项 disabled + 提示文字 |
| 11 | Lighthouse a11y | `/` Score ≥95 |
| 12 | 造 >2000 条资产（可选，用 `uv run python -c` 直接 SQL 批量插入） | 控制台 warn |
| 13 | DevTools Computed → Font Family | body 为 `Fira Sans`，`asset_code` 列为 `Fira Code`；**无 Inter/Roboto/system-ui/Geist** |
| 14 | 强制刷新 `/`，DevTools Performance 录制 | 前 20 行 stagger ≤400ms；切 filter tbody 淡切 120-160ms |
| 15 | 系统开启 "减少动画"，刷新 | stagger/淡切降级为瞬时 |

- [ ] **Step 2：按 spec 附录 A 走反模式扫（13 / 14 / 15）**

| # | 步骤 | 期望 |
|---|------|------|
| 15a | Cmd+F 搜整个 `frontend/src` 下的 `.tsx` / `.css`，关键词 `scale-` / `animate-spin` / `backdrop-blur` / `gradient` | 无匹配（spinner / 渐变背景 / blur 禁用） |
| 15b | Button hover 动画 | 仅色变，无 transform |
| 15c | 表格 hover 行 | 仅 `bg-accent/40`，无 `shadow` |

发现任何违反 §3.5 的实施细节，**立即回退组件代码**。

- [ ] **Step 3：按 MASTER `Pre-Delivery Checklist` 逐项打勾**

参考 `design-system/asset-hub/MASTER.md` 末尾 7 项：

- [ ] No emojis as icons
- [ ] cursor-pointer on all clickable elements（shadcn Button 自带；链接行在 `assets-table.tsx` 已 `cursor-pointer`）
- [ ] Hover states with smooth transitions（transition-colors 150-300ms）
- [ ] Light mode text contrast 4.5:1（Lighthouse #11 已验）
- [ ] Focus states visible（globals.css `*:focus-visible` 已保障）
- [ ] `prefers-reduced-motion` respected（#15）
- [ ] Responsive 375/768/1024/1440（本里程碑仅要求 1024+ 可用；<1024 可横向滚动接受，M4 再 polish）

- [ ] **Step 4：如有偏差，回写 MASTER 或 assets-list**

任何 review 期决定偏离 skill 初始建议的点（例如"放弃 skill 推荐的 chart zoom 动画，因为列表页无图表"），在 `design-system/asset-hub/MASTER.md` 末尾**追加**一条：

```markdown
---
## 实施期纠偏（M2c-1）

- **忽略建议**：`Key Effects: chart zoom on click`（M2c-1 列表页无 chart；M3 看板页再评估）
- **覆盖建议**：状态色 4 态实际取值见 `globals.css` 的 `--status-*` 变量（light + dark 各一套，与 Primary/CTA 色相隔开）
```

- [ ] **Step 5：`pnpm build` / `pnpm lint` 全绿；把所有纠偏与最终修正 commit**

```bash
pnpm --dir frontend build && pnpm --dir frontend lint
git add .
git commit -m "chore(m2c1): M2c-1 最终审查与纠偏回写——frontend-design 合并前闸门通过"
```

---

## 自检清单（写完 plan 的最后一步）

本节仅作者阅读；执行者无需勾选。

**1. Spec 覆盖**：

| spec 节点 | 对应 Task |
|---|---|
| §1 目标 | 全部 |
| §2 D1-D8 关键决策 | 贯穿 |
| §3.5 审美纲领 | Task 7 (globals.css 落定) / Task 11 (StatusBadge) / Task 12 (shadcn variant) / Task 13 (AppLayout) / Task 17 (Motion 时刻 1+2) / Task 20 (合并前审查) |
| §4.2 文件结构 | 全部 Task 构成 |
| §4.3 依赖 | Task 1 + Task 13（补 router-devtools） |
| §5.1 openapi 流水线 | Task 3 |
| §5.2 QueryClient | Task 4 |
| §5.3 query-keys | Task 4 + Task 14 修正 |
| §5.4 Mutation 失效 | Task 6 |
| §5.5 URL typed search | Task 14 |
| §5.6 错误映射 | Task 4 |
| §6.1 ThemeProvider | Task 8 |
| §6.2 globals.css 策略 | Task 7 |
| §6.3 防闪烁 | Task 8 |
| §6.4 ThemeToggle | Task 9 |
| §6.5 字体 | Task 7 |
| §7.1 AppLayout | Task 13 |
| §7.2 列表页 | Task 14–19 |
| §7.3 公共组件 | Task 10 + Task 11 |
| §8 错误处理 4 层 | Task 4 (mutation/query) + Task 10 (ErrorBoundary) + Task 14 (Router validateSearch 兜底) |
| §9 不引入 Vitest | 全部 Task 用 build+lint+手工验证 |
| §10 DoD | Task 20 |
| 附录 A 烟测 | Task 20 |

**2. Placeholder 扫描**：grep `TBD|TODO|implement later` ——本 plan 无匹配 ✓。

**3. 类型一致**：
- `AssetsSearch` 从 `search-schema.ts` 导出，Task 4/6/14/15/17/18/19 统一 import ✓
- `AssetStatus` 从 `status-labels.ts` 导出，Task 14/17 import ✓
- `ColumnKey` 从 `column-visibility.tsx` 导出，Task 17 import ✓
- `AssetRow` 从 `assets-table.tsx` 导出（Task 19 Step 2 明确），Task 19 import ✓

**4. frontend-design 隐性 shadcn 默认扫描**（spec §3.4 ③ 要求）：
- Button / Input / Select / DropdownMenu 的 variant 审查集中在 Task 12，**禁 transform scale**、**focus ring 走 globals** 两条红线写入步骤 ✓
- 无 `shadcn Card` 的使用（避免典型"卡片堆叠"AI 模板脸） ✓
- StatusBadge 独立实现，**不**走 shadcn `Badge.variant` ——避免污染 Badge 的 variant 空间（Task 11） ✓
- 所有 `rounded-*` 通过 `--radius=0.375rem` 自动缩小；无直接 `rounded-xl / rounded-2xl` 硬编码 ✓
- 无渐变背景、无 backdrop-blur、无多层 shadow（Task 20 Step 2 扫描 ✓）

---

**Plan complete and saved to `docs/superpowers/plans/2026-04-24-m2c1-frontend-foundation-and-list.md`. Two execution options:**

**1. Subagent-Driven (recommended)** - 我派发 fresh subagent 逐 Task 实施，Task 间可 review，迭代快

**2. Inline Execution** - 在当前会话里执行，批量带 checkpoints

**Which approach?**
