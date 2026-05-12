import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { DeclareUnrepairableAlertDialog } from "@/features/assets/detail/declare-unrepairable-alert-dialog";

const wrapper = ({ children }: { children: React.ReactNode }) => {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
};

describe("DeclareUnrepairableAlertDialog", () => {
  it("渲染时显示 title 和 description", () => {
    render(
      <DeclareUnrepairableAlertDialog
        open={true}
        onOpenChange={() => {}}
        assetId="asset-1"
        assetName="MacBook Pro"
      />,
      { wrapper },
    );
    // title text appears in badge + heading; use heading role to pinpoint
    expect(screen.getByRole("heading", { name: "判定不可修复" })).toBeInTheDocument();
    expect(screen.getByText(/MacBook Pro/)).toBeInTheDocument();
    expect(screen.getByText(/送修.*故障/)).toBeInTheDocument();
  });

  it("显示确认判定按钮", () => {
    render(
      <DeclareUnrepairableAlertDialog
        open={true}
        onOpenChange={() => {}}
        assetId="asset-1"
        assetName="测试设备"
      />,
      { wrapper },
    );
    expect(screen.getByRole("button", { name: "确认不可修复" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "取消" })).toBeInTheDocument();
  });

  it("显示备注文本框", () => {
    render(
      <DeclareUnrepairableAlertDialog
        open={true}
        onOpenChange={() => {}}
        assetId="asset-1"
        assetName="测试设备"
      />,
      { wrapper },
    );
    expect(screen.getByPlaceholderText("判定备注（可选）")).toBeInTheDocument();
  });
});
