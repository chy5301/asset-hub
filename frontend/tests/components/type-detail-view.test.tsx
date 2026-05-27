import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import {
  createMemoryHistory,
  createRouter,
  RouterProvider,
  createRootRoute,
  createRoute,
  Outlet,
} from "@tanstack/react-router";

import { TypeDetailView } from "@/features/types/detail/type-detail-view";
import type { TypeRead } from "@/features/assets/types";

const type: TypeRead = {
  id: "t1",
  name: "笔记本",
  code_prefix: "NB",
  description: "便携电脑",
  custom_fields: [],
  ref_count: 3,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-02-01T00:00:00Z",
} as TypeRead;

function renderWithRouter(ui: React.ReactNode) {
  const rootRoute = createRootRoute({ component: () => <Outlet /> });
  const indexRoute = createRoute({
    getParentRoute: () => rootRoute,
    path: "/",
    component: () => <>{ui}</>,
  });
  const router = createRouter({
    routeTree: rootRoute.addChildren([indexRoute]),
    history: createMemoryHistory({ initialEntries: ["/"] }),
  });
  return render(<RouterProvider router={router} />);
}

describe("TypeDetailView", () => {
  it("渲染类型名标题 + 返回链接 + 元信息 + 资产引用数", async () => {
    renderWithRouter(<TypeDetailView type={type} onDelete={vi.fn()} />);
    expect(
      await screen.findByRole("heading", { name: "笔记本" }),
    ).toBeInTheDocument();
    expect(screen.getByText("← 返回类型列表")).toBeInTheDocument();
    expect(screen.getAllByText("NB").length).toBeGreaterThanOrEqual(2);
    expect(screen.getByText("3")).toBeInTheDocument();
  });

  it("有编辑按钮", async () => {
    renderWithRouter(<TypeDetailView type={type} onDelete={vi.fn()} />);
    expect(
      await screen.findByRole("link", { name: "编辑" }),
    ).toBeInTheDocument();
  });
});
