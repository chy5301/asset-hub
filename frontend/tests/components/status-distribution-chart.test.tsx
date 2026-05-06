import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { StatusDistributionChart } from "@/features/dashboard/charts/status-distribution-chart";

describe("StatusDistributionChart", () => {
  it("renders empty state when data is null", () => {
    render(<StatusDistributionChart data={null} />);
    expect(screen.getByText(/还没有登记任何资产/)).toBeInTheDocument();
  });

  it("renders empty state when all counts are 0", () => {
    render(<StatusDistributionChart data={{ IDLE: 0, IN_USE: 0 }} />);
    expect(screen.getByText(/还没有登记任何资产/)).toBeInTheDocument();
  });

  it("renders 3 segments + counts for default 3-state", () => {
    render(<StatusDistributionChart data={{ IDLE: 78, IN_USE: 92, MAINTENANCE: 12 }} />);
    // 每个 count 在 segment 内 + dot legend 各出现一次
    expect(screen.getAllByText("92")).toHaveLength(2);
    expect(screen.getAllByText("78")).toHaveLength(2);
    expect(screen.getAllByText("12")).toHaveLength(2);
  });

  it("renders dot legend labels", () => {
    render(<StatusDistributionChart data={{ IDLE: 5, IN_USE: 5 }} />);
    expect(screen.getByText("在用")).toBeInTheDocument();
    expect(screen.getByText("闲置")).toBeInTheDocument();
  });
});
