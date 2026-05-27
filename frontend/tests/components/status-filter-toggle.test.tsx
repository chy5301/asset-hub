import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { Moon } from "lucide-react";

import { StatusFilterToggle } from "@/components/status/status-filter-toggle";

describe("StatusFilterToggle", () => {
  it("渲染 label + 图标，aria-label 正确", () => {
    render(
      <StatusFilterToggle
        pressed={false}
        onPressedChange={vi.fn()}
        icon={Moon}
        label="显示退役"
        status="retired"
      />,
    );
    expect(screen.getByRole("button", { name: "显示退役" })).toBeInTheDocument();
  });

  it("pressed 时 data-state=on，点击回调切换", () => {
    const onChange = vi.fn();
    render(
      <StatusFilterToggle
        pressed={true}
        onPressedChange={onChange}
        icon={Moon}
        label="显示退役"
        status="retired"
      />,
    );
    const btn = screen.getByRole("button", { name: "显示退役" });
    expect(btn).toHaveAttribute("data-state", "on");
    fireEvent.click(btn);
    expect(onChange).toHaveBeenCalledWith(false);
  });
});
