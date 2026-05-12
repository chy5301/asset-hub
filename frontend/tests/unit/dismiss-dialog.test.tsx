import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { DismissDialog } from "@/features/assets/detail/dismiss-dialog";

const wrapper = ({ children }: { children: React.ReactNode }) => {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
};

describe("DismissDialog", () => {
  it("渲染时显示 title 和 description", () => {
    render(
      <DismissDialog
        open={true}
        onOpenChange={() => {}}
        assetId="asset-1"
        currentHolder="张三"
        currentLocation="仓库A"
      />,
      { wrapper },
    );
    expect(screen.getByText("解除故障")).toBeInTheDocument();
    expect(screen.getByText(/故障态回到闲置/)).toBeInTheDocument();
  });

  it("预填 currentHolder 和 currentLocation", () => {
    render(
      <DismissDialog
        open={true}
        onOpenChange={() => {}}
        assetId="asset-1"
        currentHolder="李四"
        currentLocation="机房B"
      />,
      { wrapper },
    );
    expect(screen.getByDisplayValue("李四")).toBeInTheDocument();
    expect(screen.getByDisplayValue("机房B")).toBeInTheDocument();
  });

  it("显示持有人和位置 label", () => {
    render(
      <DismissDialog
        open={true}
        onOpenChange={() => {}}
        assetId="asset-1"
        currentHolder={null}
        currentLocation={null}
      />,
      { wrapper },
    );
    expect(screen.getByText("持有人（可选）")).toBeInTheDocument();
    expect(screen.getByText("位置（可选）")).toBeInTheDocument();
    expect(screen.getByText("备注（可选）")).toBeInTheDocument();
  });
});
