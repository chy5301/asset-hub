import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ReportBrokenDialog } from "@/features/assets/detail/report-broken-dialog";

const wrapper = ({ children }: { children: React.ReactNode }) => {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
};

describe("ReportBrokenDialog", () => {
  it("渲染时显示标题和描述", () => {
    render(
      <ReportBrokenDialog
        open={true}
        onOpenChange={() => {}}
        assetId="asset-1"
        currentHolder="张三"
        currentLocation="仓库A"
      />,
      { wrapper },
    );
    expect(screen.getByText("标记出现故障")).toBeInTheDocument();
    expect(screen.getByText(/资产状态变为/)).toBeInTheDocument();
  });

  it("预填 currentHolder 和 currentLocation", () => {
    render(
      <ReportBrokenDialog
        open={true}
        onOpenChange={() => {}}
        assetId="asset-1"
        currentHolder="张三"
        currentLocation="仓库A"
      />,
      { wrapper },
    );
    const holderInput = screen.getByDisplayValue("张三");
    const locationInput = screen.getByDisplayValue("仓库A");
    expect(holderInput).toBeInTheDocument();
    expect(locationInput).toBeInTheDocument();
  });

  it("显示持有人和位置 label", () => {
    render(
      <ReportBrokenDialog
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
