import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  createMemoryHistory,
  createRouter,
  RouterProvider,
  createRootRoute,
  createRoute,
  Outlet,
} from "@tanstack/react-router";

import { AssetTitleAccessory } from "@/features/assets/detail/asset-header";
import * as transitionsHook from "@/api/hooks/transitions";
import type { AssetRead, TransitionRead } from "@/features/assets/types";

const baseAsset: AssetRead = {
  id: "a1",
  asset_code: "NB-001",
  name: "ThinkPad",
  serial_number: null,
  type_id: "t1",
  type_name: "笔记本",
  status: "IN_USE",
  holder: "张三",
  location: "工位 A1",
  notes: null,
  custom_data: {},
  acquired_at: null,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-04-20T00:00:00Z",
  idle_days: 0,
} as AssetRead;

function mkOpen(due_at: string | null): TransitionRead {
  return {
    id: "co1",
    asset_id: "a1",
    kind: "CHECKOUT_INTERNAL",
    from_status: "IDLE",
    to_status: "IN_USE",
    from_holder: null,
    to_holder: "张三",
    from_location: null,
    to_location: "工位 A1",
    note: null,
    created_at: "2026-04-20T10:00:00Z",
    due_at,
    closes_transition_id: null,
  } as TransitionRead;
}

function renderWithProviders(ui: React.ReactNode) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  const rootRoute = createRootRoute({ component: () => <Outlet /> });
  const indexRoute = createRoute({
    getParentRoute: () => rootRoute,
    path: "/",
    component: () => <>{ui}</>,
    validateSearch: (s: Record<string, unknown>) => s,
  });
  const router = createRouter({
    routeTree: rootRoute.addChildren([indexRoute]),
    history: createMemoryHistory({ initialEntries: ["/"] }),
  });
  return render(
    <QueryClientProvider client={qc}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  );
}

describe("AssetHeader overdue 角标 (M3d)", () => {
  beforeEach(() => {
    vi.useFakeTimers({
      shouldAdvanceTime: true,
    });
    vi.setSystemTime(new Date("2026-01-15T12:00:00Z"));
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("status IN_USE + dueAt 8 天前 + OPEN CHECKOUT → render 逾期 N 天 红角标", async () => {
    const dueAt = "2026-01-07T12:00:00Z"; // 8 天前
    vi.spyOn(transitionsHook, "useTransitionsQuery").mockReturnValue({
      data: [mkOpen(dueAt)],
      isLoading: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    } as never);

    renderWithProviders(
      <AssetTitleAccessory asset={{ ...baseAsset, status: "IN_USE" }} />,
    );
    expect(await screen.findByText(/逾期 \d+ 天/)).toBeInTheDocument();
  });

  it("status IDLE + dueAt 任意 → 不 render 角标", async () => {
    vi.spyOn(transitionsHook, "useTransitionsQuery").mockReturnValue({
      data: [],
      isLoading: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    } as never);

    renderWithProviders(
      <span data-testid="anchor">
        <AssetTitleAccessory asset={{ ...baseAsset, status: "IDLE" }} />
      </span>,
    );
    // 等路由 mount 完（anchor 元素）
    await screen.findByTestId("anchor");
    expect(screen.queryByText(/逾期|还有/)).not.toBeInTheDocument();
  });

  it("status IN_USE + dueAt null → 不 render 角标", async () => {
    vi.spyOn(transitionsHook, "useTransitionsQuery").mockReturnValue({
      data: [mkOpen(null)],
      isLoading: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    } as never);

    renderWithProviders(
      <span data-testid="anchor">
        <AssetTitleAccessory asset={{ ...baseAsset, status: "IN_USE" }} />
      </span>,
    );
    await screen.findByTestId("anchor");
    expect(screen.queryByText(/逾期|还有/)).not.toBeInTheDocument();
  });

  it("status IN_USE + dueAt 5 天后 → render 还有 N 天到期 黄角标", async () => {
    const dueAt = "2026-01-20T12:00:00Z"; // 5 天后
    vi.spyOn(transitionsHook, "useTransitionsQuery").mockReturnValue({
      data: [mkOpen(dueAt)],
      isLoading: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    } as never);

    renderWithProviders(
      <AssetTitleAccessory asset={{ ...baseAsset, status: "IN_USE" }} />,
    );
    expect(await screen.findByText(/还有 \d+ 天到期/)).toBeInTheDocument();
  });

  it("OPEN + 已 closed CHECKOUT 共存 → 角标对应新 OPEN 的 due_at（验 closes_transition_id 排除）", async () => {
    // 用 8 天前 due_at 给旧 closed CHECKOUT；用 3 天前 due_at 给新 OPEN CHECKOUT
    // 如果 closedIds 排除逻辑漏了，会拿到最新（含新旧两个 CHECKOUT）但可能误用旧 due_at
    const newOpenDueAt = "2026-01-12T12:00:00Z"; // 3 天前（固定 ISO，时区无关）
    const oldClosedDueAt = "2026-01-07T12:00:00Z"; // 8 天前（固定 ISO，时区无关）

    const transitions: TransitionRead[] = [
      // desc 顺序：最新 OPEN
      {
        id: "co_new",
        asset_id: "a1",
        kind: "CHECKOUT_INTERNAL",
        from_status: "IDLE",
        to_status: "IN_USE",
        from_holder: null,
        to_holder: "李四",
        from_location: null,
        to_location: "工位 B2",
        note: null,
        created_at: "2026-04-25T10:00:00Z",
        due_at: newOpenDueAt,
        closes_transition_id: null,
      } as TransitionRead,
      // 旧 RETURN closes 旧 CHECKOUT
      {
        id: "ret_old",
        asset_id: "a1",
        kind: "RETURN",
        from_status: "IN_USE",
        to_status: "IDLE",
        from_holder: "张三",
        to_holder: null,
        from_location: "工位 A1",
        to_location: null,
        note: null,
        created_at: "2026-04-15T10:00:00Z",
        due_at: null,
        closes_transition_id: "co_old",
      } as TransitionRead,
      // 旧 CHECKOUT（已被 closed）
      {
        id: "co_old",
        asset_id: "a1",
        kind: "CHECKOUT_INTERNAL",
        from_status: "IDLE",
        to_status: "IN_USE",
        from_holder: null,
        to_holder: "张三",
        from_location: null,
        to_location: "工位 A1",
        note: null,
        created_at: "2026-04-01T10:00:00Z",
        due_at: oldClosedDueAt,
        closes_transition_id: null,
      } as TransitionRead,
    ];

    vi.spyOn(transitionsHook, "useTransitionsQuery").mockReturnValue({
      data: transitions,
      isLoading: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    } as never);

    renderWithProviders(
      <AssetTitleAccessory asset={{ ...baseAsset, status: "IN_USE" }} />,
    );
    // 必须显示"逾期 3 天"（新 OPEN），不是"逾期 8 天"（旧 closed）
    expect(await screen.findByText(/逾期 3 天/)).toBeInTheDocument();
    expect(screen.queryByText(/逾期 8 天/)).not.toBeInTheDocument();
  });
});
