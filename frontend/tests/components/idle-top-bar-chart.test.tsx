import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { IdleTopBarChart } from "@/features/dashboard/charts/idle-top-bar-chart";

vi.mock("@tanstack/react-router", () => ({
  Link: ({ to, children, ...rest }: { to: string; children: React.ReactNode }) => (
    <a href={to} {...rest}>{children}</a>
  ),
}));

const item90plus = {
  asset_id: "1",
  asset_code: "G-001",
  name: "NVIDIA A100 显卡",
  type_name: "GPU",
  current_location: "仓库",
  idle_days: 152,
  idle_since: "2025-12-04T00:00:00Z",
};
const itemUnder90 = {
  asset_id: "2",
  asset_code: "L-002",
  name: "ThinkPad X1 Carbon",
  type_name: "Laptop",
  current_location: null,
  idle_days: 30,
  idle_since: "2026-04-06T00:00:00Z",
};

describe("IdleTopBarChart", () => {
  it("renders empty state with '没有闲置资产' when data is []", () => {
    render(<IdleTopBarChart data={[]} />);
    expect(screen.getByText(/没有闲置资产/)).toBeInTheDocument();
  });

  it("renders section header when data exists", () => {
    render(<IdleTopBarChart data={[item90plus, itemUnder90]} />);
    expect(screen.getByText("闲置时长 Top 10")).toBeInTheDocument();
    expect(screen.getByText(/超 90 天可考虑退役/)).toBeInTheDocument();
  });

  it("renders Recharts wrapper", () => {
    const { container } = render(<IdleTopBarChart data={[item90plus]} />);
    // Recharts 包装一个 .recharts-wrapper div (jsdom 下结构存在但 SVG layout 不准, 这里只断结构)
    expect(
      container.querySelector(".recharts-wrapper, .recharts-responsive-container"),
    ).toBeTruthy();
  });
});
