/**
 * Task 15: 验证 dashboard-page 在数据态下渲染 4 个 motion-wrapped section,
 * data-motion-kind 顺序: idle / type / status / holder.
 *
 * jsdom 不实际跑 animation, 仅断 motion.div 的 DOM 结构 + data-attr 顺序.
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import type { ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";

import { DashboardPage } from "@/features/dashboard/dashboard-page";

type MswServer = ReturnType<typeof setupServer>;
const server = (globalThis as unknown as { __mswServer: MswServer }).__mswServer;

// mock TanStack Router: DashboardPage 使用 DashboardRoute.useSearch / useNavigate
vi.mock("@/routes/dashboard", () => ({
  Route: {
    useSearch: () => ({ include_retired: false, include_disposed: false }),
    useNavigate: () => vi.fn(),
  },
}));

// 防御性 mock: EmptyCard 内部可能用 Link, 即便非空态也提前避免意外加载真实 router
vi.mock("@tanstack/react-router", () => ({
  Link: ({ to, children }: { to: string; children: ReactNode }) => (
    <a href={to}>{children}</a>
  ),
}));

describe("DashboardPage motion", () => {
  it("renders 4 motion-wrapped sections in correct order", async () => {
    server.use(
      http.get("http://localhost:3000/api/stats", () =>
        HttpResponse.json({
          type_distribution: [{ type_id: "1", type_name: "Laptop", count: 10 }],
          status_distribution: { IDLE: 5, IN_USE: 5 },
          holder_ranking: [{ holder: "张三", count: 5 }],
          idle_top: [
            {
              asset_id: "x",
              asset_code: "L-001",
              type_name: "L",
              current_location: null,
              idle_days: 30,
              idle_since: "2026-04-01T00:00:00Z",
            },
          ],
          summary: {
            total_assets: 10,
            registered_assets: 10,
            idle_count: 5,
            include_retired: false,
            include_disposed: false,
            generated_at: "2026-05-06T10:00:00Z",
          },
        }),
      ),
    );

    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    const { container, findByText } = render(
      <QueryClientProvider client={qc}>
        <DashboardPage />
      </QueryClientProvider>,
    );

    // 等待数据加载完成 (h2 "闲置时长 Top 10" 出现)
    await findByText("闲置时长 Top 10");

    const motionKinds = Array.from(
      container.querySelectorAll("[data-motion-kind]"),
    ).map((el) => el.getAttribute("data-motion-kind"));

    expect(motionKinds).toEqual(["idle", "type", "status", "holder"]);
  });
});
