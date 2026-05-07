# M3c PR-2 实施计划: 前端 ExportButton + filter 透传

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 列表页 filter bar 加 `导出 ▾` DropdownMenu (Excel / CSV), 把当前 `AssetsSearch` 序列化为 query string + 名字翻译 (`show_retired` → `include_retired`), 触发 `GET /api/export` 浏览器原生下载. 完成 M3c 闭环.

**Architecture:** 单组件 `ExportButton` 复用项目现有 `DropdownMenu` (Radix) + `Button variant=outline` 模式 (与 `ColumnVisibilityMenu` 视觉对齐). 纯函数 `buildExportUrl(search, format)` 单独单元测试 (覆盖前端→后端字段名翻译). 触发用 `window.location.href = url` 让浏览器接管下载. PR-1 后端 `GET /api/export` 已 ship (`a55beec`), 直接消费.

**Tech Stack:** React 19 / TanStack Router / Radix DropdownMenu / Tailwind v4 / vitest + jsdom / Playwright MCP.

**Spec:** [`docs/superpowers/specs/2026-05-07-m3c-export-design.md`](../specs/2026-05-07-m3c-export-design.md) §3 + §4 + §6 (PR 拆分)

**前置约束:**

- M3c PR-1 已合到 main (`a55beec`); 后端 `/api/export` + `ExportService` ready
- `frontend/src/features/assets/list/search-schema.ts` `AssetsSearch` 类型已含 `type` / `status` / `holder` / `q` / `show_retired` / `show_disposed` (前端命名), 后端用 `include_retired` / `include_disposed` (与 list / stats 一致) — `buildExportUrl` 做字段名翻译
- `frontend/src/components/ui/dropdown-menu.tsx` 已 export `DropdownMenu` / `DropdownMenuTrigger` / `DropdownMenuContent` / `DropdownMenuItem` / `DropdownMenuLabel` / `DropdownMenuSeparator` / `DropdownMenuCheckboxItem` (Radix wrapper)
- `frontend/src/components/ui/button.tsx` `Button variant="outline" size="sm"` 是 filter bar 标准 (`ColumnVisibilityMenu` 已用)
- 项目惯例: button 含 `aria-label` + Lucide icon (`Settings2` / `Plus` 已用; export 用 `Download` icon + `ChevronDown` 表 dropdown)
- 项目 vitest jsdom 环境 `window.location.href = ...` 触发的"下载"行为不可靠 (jsdom 不实际下载) — 烟测留 Task 5 Playwright MCP
- `tsc -b` 而非 `tsc --noEmit` 做最终类型校验 (memory `feedback_tsc_verification.md`)

**任务总览** (6 任务):

1. 起分支 + 同步 OpenAPI schema
2. ExportButton 组件 + `buildExportUrl` helper (TDD)
3. 接进 `routes/index.tsx` filter bar
4. tsc -b + vitest + simplify pass
5. Playwright MCP 烟测 (浏览器原生下载验证)
6. merge --no-ff 入 main

---

## Task 1: 起分支 + 同步 OpenAPI schema

**Files:**
- Modify: `frontend/src/api/generated/schema.d.ts` (auto regenerate)

**前置**: controller 起后端 dev server (`uv run uvicorn asset_hub.api.app:app --reload &`), 等 `:8000` ready.

- [ ] **Step 1.1: 起分支**

```bash
git checkout main
git pull --ff-only origin main 2>&1 || true
git checkout -b feat/m3c-pr2-frontend
```

- [ ] **Step 1.2: 同步 schema**

```bash
pnpm --dir frontend gen:api
```

预期: `[gen-openapi] fetching http://localhost:8000/openapi.json` + `[gen-openapi] wrote .../schema.d.ts (X bytes)`.

- [ ] **Step 1.3: 验 export 端点出现**

```bash
grep -n "/api/export" frontend/src/api/generated/schema.d.ts | head -5
```

预期: 至少 1 行 (新端点路径).

注: `/api/export` 返 `Response` (bytes), 没有 response_model, 所以 OpenAPI schema 不会有 ExportRead 之类的 schema 类型 — 只在 `paths` 里看到端点路径就 OK. 前端**不消费** schema 类型 (用 `window.location.href` 直接触发).

- [ ] **Step 1.4: tsc -b 校验**

```bash
pnpm --dir frontend tsc -b
```

预期: 0 错 (schema 是新增 paths, 不影响现有代码).

- [ ] **Step 1.5: 提交**

```bash
git add frontend/src/api/generated/schema.d.ts
git status   # 验改动只含 schema.d.ts
git commit -m "$(cat <<'EOF'
chore(frontend): 同步 PR-1 export schema

新增 GET /api/export 端点 (csv/xlsx 二选一, format 必填).
EOF
)"
```

---

## Task 2: ExportButton + `buildExportUrl` helper (TDD)

**Files:**
- Create: `frontend/src/features/assets/list/export-button.tsx`
- Test: `frontend/tests/unit/list/build-export-url.test.ts` (纯函数)
- Test: `frontend/tests/components/export-button.test.tsx` (render + menu items)

`buildExportUrl` 是纯函数, 单独单元测试覆盖前端→后端字段名翻译. ExportButton render 测试只验 DropdownMenu 含 2 item + label 正确; 不测 actual 下载 (jsdom 限制 window.location, 留 Task 5 Playwright 烟测).

- [ ] **Step 2.1: 看现有 ColumnVisibilityMenu 范式**

```bash
cat frontend/src/features/assets/list/column-visibility.tsx | head -30
```

记录: `<DropdownMenu>` + `<DropdownMenuTrigger asChild><Button variant="outline" size="sm">...</Button></DropdownMenuTrigger>` + `<DropdownMenuContent align="end">...</DropdownMenuContent>`. ExportButton 沿用同模式.

- [ ] **Step 2.2: 写 buildExportUrl 测试 (纯函数)**

`frontend/tests/unit/list/build-export-url.test.ts` (新):

```typescript
import { describe, expect, it } from "vitest";

import { buildExportUrl } from "@/features/assets/list/export-button";
import type { AssetsSearch } from "@/features/assets/list/search-schema";

const baseSearch: AssetsSearch = {
  sort: "asset_code",
  page: 1,
  pageSize: 50,
};

describe("buildExportUrl", () => {
  it("minimal search → only format param", () => {
    expect(buildExportUrl(baseSearch, "csv")).toBe("/api/export?format=csv");
    expect(buildExportUrl(baseSearch, "xlsx")).toBe("/api/export?format=xlsx");
  });

  it("includes type / status / holder / q when present", () => {
    const url = buildExportUrl(
      {
        ...baseSearch,
        type: "uuid-1",
        status: "IDLE",
        holder: "张三",
        q: "笔记本",
      },
      "csv",
    );
    const params = new URLSearchParams(url.split("?")[1]);
    expect(params.get("format")).toBe("csv");
    expect(params.get("type_id")).toBe("uuid-1");
    expect(params.get("status")).toBe("IDLE");
    expect(params.get("holder")).toBe("张三");
    expect(params.get("q")).toBe("笔记本");
  });

  it("translates show_retired → include_retired", () => {
    const url = buildExportUrl(
      { ...baseSearch, show_retired: true },
      "csv",
    );
    expect(url).toContain("include_retired=true");
    expect(url).not.toContain("show_retired");
  });

  it("translates show_disposed → include_disposed", () => {
    const url = buildExportUrl(
      { ...baseSearch, show_disposed: true },
      "csv",
    );
    expect(url).toContain("include_disposed=true");
    expect(url).not.toContain("show_disposed");
  });

  it("show_retired false → no param emitted", () => {
    const url = buildExportUrl(
      { ...baseSearch, show_retired: false },
      "csv",
    );
    expect(url).not.toContain("include_retired");
  });

  it("excludes sort / page / pageSize (export 整 filter 集, 不分页)", () => {
    const url = buildExportUrl(
      { ...baseSearch, sort: "name", page: 3, pageSize: 100 },
      "csv",
    );
    const params = new URLSearchParams(url.split("?")[1]);
    expect(params.has("sort")).toBe(false);
    expect(params.has("page")).toBe(false);
    expect(params.has("pageSize")).toBe(false);
  });
});
```

- [ ] **Step 2.3: 写 ExportButton component 测试**

`frontend/tests/components/export-button.test.tsx` (新):

```tsx
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ExportButton } from "@/features/assets/list/export-button";
import type { AssetsSearch } from "@/features/assets/list/search-schema";

const baseSearch: AssetsSearch = {
  sort: "asset_code",
  page: 1,
  pageSize: 50,
};

describe("ExportButton", () => {
  it("renders a trigger button labeled 导出", () => {
    render(<ExportButton search={baseSearch} />);
    expect(
      screen.getByRole("button", { name: /导出/ }),
    ).toBeInTheDocument();
  });

  it("opens menu with Excel + CSV items on trigger click", () => {
    render(<ExportButton search={baseSearch} />);
    fireEvent.click(screen.getByRole("button", { name: /导出/ }));
    expect(screen.getByRole("menuitem", { name: /Excel/ })).toBeInTheDocument();
    expect(screen.getByRole("menuitem", { name: /CSV/ })).toBeInTheDocument();
  });

  it("Excel item renders as link with xlsx URL", () => {
    render(<ExportButton search={{ ...baseSearch, type: "uuid-1" }} />);
    fireEvent.click(screen.getByRole("button", { name: /导出/ }));
    const excelItem = screen.getByRole("menuitem", { name: /Excel/ });
    // DropdownMenuItem with asChild + <a href> 让浏览器原生下载触发
    const anchor = excelItem.closest("a") ?? excelItem.querySelector("a");
    expect(anchor).toBeTruthy();
    expect(anchor!.getAttribute("href")).toContain("format=xlsx");
    expect(anchor!.getAttribute("href")).toContain("type_id=uuid-1");
  });

  it("CSV item renders as link with csv URL", () => {
    render(<ExportButton search={baseSearch} />);
    fireEvent.click(screen.getByRole("button", { name: /导出/ }));
    const csvItem = screen.getByRole("menuitem", { name: /CSV/ });
    const anchor = csvItem.closest("a") ?? csvItem.querySelector("a");
    expect(anchor).toBeTruthy();
    expect(anchor!.getAttribute("href")).toContain("format=csv");
  });
});
```

注: 使用 `<DropdownMenuItem asChild><a href={url} download>Excel</a></DropdownMenuItem>` 模式 — 浏览器原生处理下载, jsdom 也能 render anchor 验 href. 不依赖 jsdom 的 `window.location` mock.

- [ ] **Step 2.4: 跑测试 (应失败)**

```bash
pnpm --dir frontend test -- "(build-export-url|export-button)"
```

预期: import 失败 (export-button.tsx 还没建).

- [ ] **Step 2.5: 实现 ExportButton + buildExportUrl**

`frontend/src/features/assets/list/export-button.tsx` (新):

```tsx
import { ChevronDown, Download } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

import type { AssetsSearch } from "./search-schema";

interface ExportButtonProps {
  search: AssetsSearch;
}

/**
 * 列表页"导出 ▾" DropdownMenu (spec §3 / §B.8 决议 A).
 *
 * 用 <DropdownMenuItem asChild><a href download> 让浏览器原生触发下载;
 * 不走 fetch/blob (代码最简, 浏览器 native 下载状态/错误 UI 已足够).
 */
export function ExportButton({ search }: ExportButtonProps) {
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="outline" size="sm" aria-label="导出">
          <Download className="mr-2 h-4 w-4" />
          <span>导出</span>
          <ChevronDown className="ml-2 h-4 w-4" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        <DropdownMenuItem asChild>
          <a href={buildExportUrl(search, "xlsx")} download>
            Excel
          </a>
        </DropdownMenuItem>
        <DropdownMenuItem asChild>
          <a href={buildExportUrl(search, "csv")} download>
            CSV
          </a>
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

/**
 * spec §3.1: 把 AssetsSearch 翻译为 /api/export query string.
 *
 * - 仅传 filter 字段 (type/status/holder/q/show_retired/show_disposed)
 * - 不传 sort/page/pageSize (v1 export 整 filter 集, 不分页 - spec §B.10)
 * - 字段名翻译: show_retired → include_retired (与后端 list/stats 一致)
 */
export function buildExportUrl(
  search: AssetsSearch,
  format: "csv" | "xlsx",
): string {
  const params = new URLSearchParams({ format });
  if (search.type) params.set("type_id", search.type);
  if (search.status) params.set("status", search.status);
  if (search.holder) params.set("holder", search.holder);
  if (search.q) params.set("q", search.q);
  if (search.show_retired) params.set("include_retired", "true");
  if (search.show_disposed) params.set("include_disposed", "true");
  return `/api/export?${params.toString()}`;
}
```

- [ ] **Step 2.6: 跑测试 (应通过)**

```bash
pnpm --dir frontend test -- "(build-export-url|export-button)"
```

预期: 6 (buildExportUrl) + 4 (ExportButton) = 10 PASS.

可能的失败模式:
- DropdownMenuItem `asChild` + `<a>` 在 jsdom 下 `closest('a')` / `querySelector('a')` 任一返非 null — 测试用两种 fallback (`closest('a') ?? querySelector('a')`) 应覆盖
- Radix DropdownMenu 在 jsdom 用 PointerEvent / Portal, 可能开 menu 不 render — 项目其他 dropdown 测试 (`column-visibility` 等) 应已过此关; 看 `frontend/tests/setup.ts` 是否有 PointerEvent / matchMedia mock; 若不行, 看 `column-visibility` 怎么测的对齐

- [ ] **Step 2.7: tsc -b**

```bash
pnpm --dir frontend tsc -b
```

预期: 0 错.

- [ ] **Step 2.8: 提交**

```bash
git add frontend/src/features/assets/list/export-button.tsx \
        frontend/tests/unit/list/build-export-url.test.ts \
        frontend/tests/components/export-button.test.tsx
git commit -m "$(cat <<'EOF'
feat(export): ExportButton + buildExportUrl

spec §3 / §B.8 决议 A: 单按钮"导出 ▾" + DropdownMenu (Excel / CSV);
asChild + <a href download> 让浏览器原生触发下载, 不走 fetch/blob;
buildExportUrl 翻译 show_retired/show_disposed → include_retired/include_disposed
(后端 list/stats 同字段名), 仅传 filter 字段不传 sort/page/pageSize.
EOF
)"
```

---

## Task 3: 接进 `routes/index.tsx` filter bar

**Files:**
- Modify: `frontend/src/routes/index.tsx`

- [ ] **Step 3.1: 看现状**

`frontend/src/routes/index.tsx` line 60-76 现有 filter bar 结构:

```tsx
<div className="flex flex-wrap items-center justify-between gap-3">
  <AssetsFilters search={search} />
  <div className="flex items-center gap-2">
    <ColumnVisibilityMenu visible={visible} onToggle={toggle} />
    <Link to="/assets/new">
      <Button>
        <Plus className="mr-2 h-4 w-4" />
        登记资产
      </Button>
    </Link>
  </div>
</div>
```

- [ ] **Step 3.2: 加 ExportButton**

放在 `ColumnVisibilityMenu` 后, `Link to="/assets/new"` 前 (语义顺序: 看哪些列 → 导出哪些数据 → 登记新资产):

```tsx
<div className="flex items-center gap-2">
  <ColumnVisibilityMenu visible={visible} onToggle={toggle} />
  <ExportButton search={search} />
  <Link to="/assets/new">
    ...
  </Link>
</div>
```

文件顶部 import 段加 (按字母序与现有 import 合并):

```tsx
import { ExportButton } from "@/features/assets/list/export-button";
```

- [ ] **Step 3.3: tsc + 全套测试**

```bash
pnpm --dir frontend tsc -b
pnpm --dir frontend test
```

预期: tsc 0 错; vitest 全 PASS (95 原 + 10 新 = 105 PASS).

- [ ] **Step 3.4: 提交**

```bash
git add frontend/src/routes/index.tsx
git commit -m "$(cat <<'EOF'
feat(export): 列表 filter bar 接入 ExportButton

位置: ColumnVisibilityMenu 后, '登记资产' 前 (语义顺序: 看列 → 导出 → 新增).
search prop 透传当前 filter (sort/page/pageSize 在 ExportButton 内被 buildExportUrl
过滤掉, 仅传 type/status/holder/q/show_retired/show_disposed).
EOF
)"
```

---

## Task 4: tsc -b + vitest + simplify pass

**Files:** 无新文件; 视 simplify 反馈而定的小修

- [ ] **Step 4.1: tsc -b**

```bash
pnpm --dir frontend tsc -b
```

预期: 0 错.

- [ ] **Step 4.2: vitest 全套**

```bash
pnpm --dir frontend test
```

预期: 105 PASS (95 baseline + 6 buildExportUrl + 4 ExportButton).

- [ ] **Step 4.3: simplify pass (派 3 reviewer)**

跑 `/simplify`. 关注点:

- **复用**: ExportButton 与 ColumnVisibilityMenu 视觉模式重复 (DropdownMenu + Button outline) — 是否值得抽 `IconDropdownButton` 共用 atom? Controller 决策原则: 仅 2 处用法, 不抽 (CLAUDE.md "三行相似比过早抽象好"; 抽出后两个组件需求快速分歧, 抽象会变成桎梏)
- **质量**: buildExportUrl 用 URLSearchParams 已最简; ExportButton 内 2 个 DropdownMenuItem 重复结构 — 是否抽 `<ExportFormatItem format={...} search={...} />`? 仅 2 个用法, inline 即可
- **效率**: 单组件, render 频率低; 无瓶颈

**Controller 决策**: 严格按 task 范围. reviewer 提出"超范围 refactor" (如改 ColumnVisibilityMenu / 提取共用组件) 记 follow-up, 不在 PR-2 内做.

- [ ] **Step 4.4: 修任何 critical/important issue**

如有, 单独 commit `refactor(export): simplify pass`.

- [ ] **Step 4.5: 最终验证**

```bash
pnpm --dir frontend tsc -b
pnpm --dir frontend test
```

预期: 全 PASS / 全绿.

---

## Task 5: Playwright MCP 烟测 (浏览器原生下载验证)

**Files:** 无 (controller 用 Playwright MCP 浏览器烟测)

jsdom vitest 不能验真实下载, 留浏览器实测.

- [ ] **Step 5.1: 起 dev server**

```bash
uv run asset-hub serve start --mode dev
sleep 3
curl -s http://localhost:5173 -o /dev/null -w "%{http_code}\n"   # 应 200
```

- [ ] **Step 5.2: 烟测场景**

由 controller 用 Playwright MCP 跑以下 4 场景:

| 场景 | 操作 | 期望 |
|---|---|---|
| 1. 列表页有"导出 ▾" 按钮 | `browser_navigate(:5173)` + `browser_snapshot()` | DropdownMenu 触发器在 filter bar (与列显隐 / 登记资产并排) |
| 2. 点开 menu, 见 Excel + CSV | `browser_click(导出按钮)` + `browser_snapshot()` | 2 menu item 显示 |
| 3. CSV 下载 | `browser_click(CSV item)` + 等浏览器下载 | 浏览器触发下载, URL 形如 `/api/export?format=csv` |
| 4. filter 透传 | 先 filter type/status, 再点导出 | URL 含 `type_id=...&status=...` |

每场景 `browser_take_screenshot()` 留视觉记录.

- [ ] **Step 5.3: 修任何视觉烟测发现的问题**

如:
- 按钮在 filter bar 视觉挤 → 微调 className
- DropdownMenu 内 link 样式与项目其他 dropdown 不一致 → 改样式

每修订单独 commit.

- [ ] **Step 5.4: 停 dev server**

```bash
uv run asset-hub serve stop
```

---

## Task 6: PR-2 合并 + 分支清理

**Files:** 无

- [ ] **Step 6.1: 切回 main + merge --no-ff**

```bash
git checkout main
git merge --no-ff feat/m3c-pr2-frontend -m "Merge branch 'feat/m3c-pr2-frontend' (M3c PR-2: 前端 ExportButton + filter 透传)"
git log --oneline -3
```

预期: HEAD 是 merge commit, parent[1] = `feat/m3c-pr2-frontend` HEAD.

- [ ] **Step 6.2: 清本地分支**

```bash
git branch -d feat/m3c-pr2-frontend
```

PR-2 完结即 M3c 完整就位 (后端 + 前端 + UI). 进入 M3d (timeline 视觉重构) 或按用户决定下一棒.

---

## Self-Review Checklist

实施期完成 6 task 后跑:

- [ ] spec §3 决议 (前端 ExportButton + filter 透传)
- [ ] spec §B.8 决议 A (DropdownMenu, 不用 dialog / 双按钮)
- [ ] spec §3.1 buildExportUrl 字段翻译 (show_retired → include_retired, show_disposed → include_disposed)
- [ ] spec §3.1 不含 sort / page / pageSize
- [ ] spec §3.2 接入位置 (filter bar 右侧, 与"列显隐" / "登记资产"并排)
- [ ] 测试覆盖: buildExportUrl 6 case (translation / inclusion / exclusion) + ExportButton 4 case (render / menu)
- [ ] PR commit 顺序合规 (schema → component → wire-up → simplify)
- [ ] tsc -b 全绿 / vitest 全 PASS
- [ ] Playwright MCP 4 场景烟测过

PR-2 合并即 M3c 完整就位, 进入 M3d.
