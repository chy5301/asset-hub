import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import { CheckoutDialog } from "@/features/assets/detail/checkout-dialog";
import * as transitionsHook from "@/api/hooks/transitions";

function renderWithProvider(ui: React.ReactNode) {
  const qc = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

describe("CheckoutDialog (M3d due_at picker)", () => {
  it("不填 due_at → mutation body due_at = null", async () => {
    const mockMutate = vi.fn().mockResolvedValue({});
    vi.spyOn(transitionsHook, "useRecordTransitionMutation").mockReturnValue({
      mutateAsync: mockMutate,
      isPending: false,
      isError: false,
      error: null,
      reset: vi.fn(),
    } as never);

    renderWithProvider(
      <CheckoutDialog
        open
        onOpenChange={vi.fn()}
        assetId="a1"
        kind="CHECKOUT_INTERNAL"
      />,
    );

    await userEvent.type(
      screen.getByPlaceholderText("保管人/接收方"),
      "张三",
    );
    await userEvent.click(
      screen.getByRole("button", { name: /^派发资产$|^确认派发$/ }),
    );

    expect(mockMutate).toHaveBeenCalledWith(
      expect.objectContaining({
        to_holder: "张三",
        due_at: null,
      }),
    );
  });

  it("CHECKOUT_EXTERNAL → header chip 用 status-borrowed 染色", () => {
    vi.spyOn(transitionsHook, "useRecordTransitionMutation").mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
      isError: false,
      error: null,
      reset: vi.fn(),
    } as never);

    renderWithProvider(
      <CheckoutDialog
        open
        onOpenChange={vi.fn()}
        assetId="a1"
        kind="CHECKOUT_EXTERNAL"
      />,
    );

    expect(
      document.body.querySelector(".bg-status-borrowed\\/15"),
    ).toBeInTheDocument();
  });

  it("CHECKOUT_INTERNAL → header chip 用 status-in-use 染色", () => {
    vi.spyOn(transitionsHook, "useRecordTransitionMutation").mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
      isError: false,
      error: null,
      reset: vi.fn(),
    } as never);

    renderWithProvider(
      <CheckoutDialog
        open
        onOpenChange={vi.fn()}
        assetId="a1"
        kind="CHECKOUT_INTERNAL"
      />,
    );

    expect(
      document.body.querySelector(".bg-status-in-use\\/15"),
    ).toBeInTheDocument();
  });
});
