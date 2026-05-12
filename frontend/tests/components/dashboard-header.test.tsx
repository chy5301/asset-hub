import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { DashboardHeader } from "@/features/dashboard/dashboard-header";

describe("DashboardHeader", () => {
  it("renders h1 + subtitle", () => {
    render(<DashboardHeader includeRetired={false} includeDisposed={false} onToggle={vi.fn()} />);
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent("看板");
    expect(screen.getByText(/实时盘点/)).toBeInTheDocument();
  });

  it("toggle pills reflect prop state via data-state", () => {
    render(<DashboardHeader includeRetired={true} includeDisposed={false} onToggle={vi.fn()} />);
    expect(screen.getByRole("button", { name: /已退役/ })).toHaveAttribute("data-state", "on");
    expect(screen.getByRole("button", { name: /已注销/ })).toHaveAttribute("data-state", "off");
  });

  it("clicking pill calls onToggle with toggled state", () => {
    const onToggle = vi.fn();
    render(<DashboardHeader includeRetired={false} includeDisposed={false} onToggle={onToggle} />);
    fireEvent.click(screen.getByRole("button", { name: /已退役/ }));
    expect(onToggle).toHaveBeenCalledWith({ include_retired: true, include_disposed: false });
  });

  it("hint icon renders with title attr", () => {
    render(<DashboardHeader includeRetired={false} includeDisposed={false} onToggle={vi.fn()} />);
    expect(screen.getByTitle(/默认排除/)).toBeInTheDocument();
  });
});
