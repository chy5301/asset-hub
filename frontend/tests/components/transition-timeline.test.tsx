import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import { TransitionTimeline } from "@/features/assets/detail/transition-timeline";
import * as transitionsHook from "@/api/hooks/transitions";
import type { TransitionRead } from "@/features/assets/types";

function mkT(id: string, kind: TransitionRead["kind"], created_at: string, extra: Partial<TransitionRead> = {}): TransitionRead {
  return {
    id, asset_id: "a1", kind,
    from_status: null, to_status: "IDLE",
    from_holder: null, to_holder: "张三",
    from_location: null, to_location: "工位 A1",
    note: null, created_at, due_at: null, closes_transition_id: null,
    ...extra,
  } as TransitionRead;
}

function renderWithProvider(ui: React.ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

describe("TransitionTimeline (M3d)", () => {
  it("跨 2 个月数据 → 渲染 2 个月份 heading", () => {
    const data = [
      mkT("t1", "DISPOSE", "2026-05-02T10:00:00Z"),
      mkT("t2", "RETIRE", "2026-04-15T10:00:00Z"),
    ];
    vi.spyOn(transitionsHook, "useTransitionsQuery").mockReturnValue({
      data, isLoading: false, isError: false, error: null, refetch: vi.fn(),
    } as never);

    renderWithProvider(<TransitionTimeline assetId="a1" assetStatus="DISPOSED" />);

    expect(screen.getByText("2026-05")).toBeInTheDocument();
    expect(screen.getByText("2026-04")).toBeInTheDocument();
  });

  it("CHECKOUT + RETURN 一对 → DOM 含派发 + 归还 pill 文案", () => {
    const data = [
      mkT("ret", "RETURN", "2026-05-05T10:00:00Z", { closes_transition_id: "co" }),
      mkT("co", "CHECKOUT_INTERNAL", "2026-04-20T10:00:00Z"),
    ];
    vi.spyOn(transitionsHook, "useTransitionsQuery").mockReturnValue({
      data, isLoading: false, isError: false, error: null, refetch: vi.fn(),
    } as never);

    renderWithProvider(<TransitionTimeline assetId="a1" assetStatus="IDLE" />);

    expect(screen.getByText("派发给 张三 · 位置 工位 A1")).toBeInTheDocument();
    expect(screen.getByText("归还给 张三")).toBeInTheDocument();
  });

  it("时间格式 = 绝对日期 · 相对天数", () => {
    const data = [mkT("t1", "RETIRE", "2026-05-02T10:00:00Z")];
    vi.spyOn(transitionsHook, "useTransitionsQuery").mockReturnValue({
      data, isLoading: false, isError: false, error: null, refetch: vi.fn(),
    } as never);

    renderWithProvider(<TransitionTimeline assetId="a1" assetStatus="RETIRED" />);

    // 不强测 "5 天前"（依赖运行日期）；强测格式存在 yyyy-MM-dd · X 天前 / 今天 / 昨天
    const time = screen.getByText(/^2026-05-02 · /);
    expect(time).toBeInTheDocument();
  });

  it("loading → 渲染 skeleton（不显示月份分组）", () => {
    vi.spyOn(transitionsHook, "useTransitionsQuery").mockReturnValue({
      data: undefined, isLoading: true, isError: false, error: null, refetch: vi.fn(),
    } as never);

    renderWithProvider(<TransitionTimeline assetId="a1" assetStatus="IDLE" />);

    expect(screen.queryByText(/^\d{4}-\d{2}$/)).not.toBeInTheDocument();
  });

  it("empty → 渲染 EmptyState", () => {
    vi.spyOn(transitionsHook, "useTransitionsQuery").mockReturnValue({
      data: [], isLoading: false, isError: false, error: null, refetch: vi.fn(),
    } as never);

    renderWithProvider(<TransitionTimeline assetId="a1" assetStatus="IDLE" />);

    expect(screen.getByText(/暂无流转记录/)).toBeInTheDocument();
  });
});
