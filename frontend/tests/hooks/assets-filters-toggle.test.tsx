/**
 * assets-filters Toggle on/off → URL search params 同步。
 * M3e §3.2 薄弱点补测前端层。
 *
 * AssetsFilters 依赖：
 *   - useNavigate (TanStack Router)
 *   - useAssetTypesQuery (react-query hook)
 * 测试策略：
 *   - 用 createRouter + RouterProvider 提供真实路由上下文
 *   - mock useAssetTypesQuery 返回空列表（避免 HTTP 请求）
 *   - 点击 Toggle 后断言 router.state.location.searchStr 含 show_retired / show_disposed
 */
import { describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  createMemoryHistory,
  createRootRoute,
  createRoute,
  createRouter,
  Outlet,
  RouterProvider,
} from "@tanstack/react-router";

import { AssetsFilters } from "@/features/assets/list/assets-filters";
import type { AssetsSearch } from "@/features/assets/list/search-schema";

// mock useAssetTypesQuery 返回空列表，避免真实 HTTP 请求
vi.mock("@/api/hooks/types", () => ({
  useAssetTypesQuery: () => ({ data: [], isLoading: false, isError: false }),
}));

const defaultSearch: AssetsSearch = {
  sort: "asset_code",
  page: 1,
  pageSize: 50,
};

function renderFiltersWithRouter(search: AssetsSearch = defaultSearch) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const rootRoute = createRootRoute({ component: () => <Outlet /> });
  const indexRoute = createRoute({
    getParentRoute: () => rootRoute,
    path: "/",
    component: () => <AssetsFilters search={search} />,
    validateSearch: (s: Record<string, unknown>) => s as AssetsSearch,
  });
  const router = createRouter({
    routeTree: rootRoute.addChildren([indexRoute]),
    history: createMemoryHistory({ initialEntries: ["/"] }),
  });
  render(
    <QueryClientProvider client={qc}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  );
  return { router };
}

describe("AssetsFilters Toggle URL sync", () => {
  it("toggle 显示已退役 → URL 加 show_retired=true", async () => {
    const user = userEvent.setup();
    const { router } = renderFiltersWithRouter();

    // 等组件挂载完成
    const toggle = await screen.findByRole("button", { name: "显示已退役资产" });
    await user.click(toggle);

    await waitFor(() => {
      expect(router.state.location.searchStr).toContain("show_retired=true");
    });
  });

  it("toggle 显示已处置 → URL 加 show_disposed=true", async () => {
    const user = userEvent.setup();
    const { router } = renderFiltersWithRouter();

    const toggle = await screen.findByRole("button", { name: "显示已处置资产" });
    await user.click(toggle);

    await waitFor(() => {
      expect(router.state.location.searchStr).toContain("show_disposed=true");
    });
  });
});
