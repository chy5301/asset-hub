import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { SimpleTransitionDialog } from "@/features/assets/detail/simple-transition-dialog";

const wrapper = ({ children }: { children: React.ReactNode }) => {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
};

describe("SimpleTransitionDialog – REPORT_BROKEN kind", () => {
  it("显示标题'出现故障资产'和描述", () => {
    render(
      <SimpleTransitionDialog
        open={true}
        onOpenChange={() => {}}
        assetId="asset-1"
        kind="REPORT_BROKEN"
        currentHolder="张三"
        currentLocation="仓库A"
      />,
      { wrapper },
    );
    expect(screen.getByText("出现故障资产")).toBeInTheDocument();
    expect(screen.getByText(/资产状态变为/)).toBeInTheDocument();
  });

  it("预填 currentHolder 和 currentLocation", () => {
    render(
      <SimpleTransitionDialog
        open={true}
        onOpenChange={() => {}}
        assetId="asset-1"
        kind="REPORT_BROKEN"
        currentHolder="张三"
        currentLocation="仓库A"
      />,
      { wrapper },
    );
    expect(screen.getByDisplayValue("张三")).toBeInTheDocument();
    expect(screen.getByDisplayValue("仓库A")).toBeInTheDocument();
  });
});

describe("SimpleTransitionDialog – DISMISS kind", () => {
  it("显示标题'故障解除资产'和描述", () => {
    render(
      <SimpleTransitionDialog
        open={true}
        onOpenChange={() => {}}
        assetId="asset-1"
        kind="DISMISS"
        currentHolder="李四"
        currentLocation="机房B"
      />,
      { wrapper },
    );
    expect(screen.getByText("故障解除资产")).toBeInTheDocument();
    expect(screen.getByText(/故障态回到闲置/)).toBeInTheDocument();
  });

  it("预填 currentHolder 到 to_holder input", () => {
    render(
      <SimpleTransitionDialog
        open={true}
        onOpenChange={() => {}}
        assetId="asset-1"
        kind="DISMISS"
        currentHolder="李四"
        currentLocation={null}
      />,
      { wrapper },
    );
    expect(screen.getByDisplayValue("李四")).toBeInTheDocument();
  });
});

describe("SimpleTransitionDialog – 原有 kinds", () => {
  it("SEND_TO_MAINTENANCE 渲染正确标题", () => {
    render(
      <SimpleTransitionDialog
        open={true}
        onOpenChange={() => {}}
        assetId="asset-1"
        kind="SEND_TO_MAINTENANCE"
      />,
      { wrapper },
    );
    expect(screen.getByText("送修资产")).toBeInTheDocument();
  });

  it("REINSTATE 渲染正确标题", () => {
    render(
      <SimpleTransitionDialog
        open={true}
        onOpenChange={() => {}}
        assetId="asset-1"
        kind="REINSTATE"
      />,
      { wrapper },
    );
    expect(screen.getByText("重新启用资产")).toBeInTheDocument();
  });
});
