import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { TypeDistributionChart } from "@/features/dashboard/charts/type-distribution-chart";

vi.mock("@tanstack/react-router", () => ({
  Link: ({ to, children, ...rest }: { to: string; children: React.ReactNode }) => (
    <a href={to} {...rest}>{children}</a>
  ),
}));

describe("TypeDistributionChart", () => {
  it("renders empty state when data is []", () => {
    render(<TypeDistributionChart data={[]} />);
    expect(screen.getByText(/尚未定义任何类型/)).toBeInTheDocument();
  });

  it("renders donut center total = sum of counts", () => {
    render(
      <TypeDistributionChart
        data={[
          { type_id: "1", type_name: "Laptop", count: 71 },
          { type_id: "2", type_name: "GPU", count: 38 },
        ]}
      />,
    );
    expect(screen.getByText("109")).toBeInTheDocument();
    expect(screen.getByText("件")).toBeInTheDocument();
  });

  it("renders legend rows with type_name + count", () => {
    render(
      <TypeDistributionChart
        data={[{ type_id: "1", type_name: "Laptop", count: 71 }]}
      />,
    );
    expect(screen.getByText("Laptop")).toBeInTheDocument();
    // 单条数据时中心总数 = 唯一项 count, 两个 "71" 同时出现 (center + legend)
    expect(screen.getAllByText("71")).toHaveLength(2);
  });
});
