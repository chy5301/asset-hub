import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { HolderLeaderboard } from "@/features/dashboard/charts/holder-leaderboard";

describe("HolderLeaderboard", () => {
  it("renders empty state when data is []", () => {
    render(<HolderLeaderboard data={[]} />);
    expect(screen.getByText(/还没有派发记录/)).toBeInTheDocument();
  });

  it("renders all rows", () => {
    render(
      <HolderLeaderboard
        data={[
          { holder: "张三", count: 28 },
          { holder: "李四", count: 21 },
        ]}
      />,
    );
    expect(screen.getByText("张三")).toBeInTheDocument();
    expect(screen.getByText("李四")).toBeInTheDocument();
    expect(screen.getByText("28")).toBeInTheDocument();
    expect(screen.getByText("21")).toBeInTheDocument();
  });

  it("first holder mini bar fills 100%, second proportional", () => {
    const { container } = render(
      <HolderLeaderboard
        data={[
          { holder: "张三", count: 28 },
          { holder: "李四", count: 14 },
        ]}
      />,
    );
    const bars = container.querySelectorAll('[data-testid="holder-mini-bar-fill"]');
    expect(bars).toHaveLength(2);
    expect((bars[0] as HTMLElement).style.width).toBe("100%");
    expect((bars[1] as HTMLElement).style.width).toBe("50%");
  });
});
