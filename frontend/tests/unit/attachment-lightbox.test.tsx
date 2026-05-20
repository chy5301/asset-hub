import { describe, it, expect, beforeEach, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { AttachmentLightbox } from "@/features/assets/detail/attachment-lightbox";
import type { AttachmentRead } from "@/features/assets/types";

// Mock dependencies
vi.mock("@/api/hooks/attachments", () => ({
  useDeleteAttachmentMutation: vi.fn(() => ({
    mutateAsync: vi.fn(),
    error: null,
    reset: vi.fn(),
    isPending: false,
  })),
}));

const mockAttachment: AttachmentRead = {
  id: "att-1",
  original_name: "test.png",
  mime_type: "image/png",
  size: 1024,
  sha256: "abc123",
  uploaded_at: "2026-01-01T00:00:00Z",
};

describe("AttachmentLightbox", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("DialogContent 应有 !max-w-[90vw] 覆盖 sm:max-w-sm 默认", () => {
    const { container } = render(
      <AttachmentLightbox
        attachment={mockAttachment}
        assetId="asset-1"
        onClose={() => {}}
      />,
    );

    // Find the DialogContent element (the one with the lightbox content)
    const dialogContent = container.querySelector('[data-slot="dialog-content"]');
    expect(dialogContent).toBeTruthy();
    expect(dialogContent?.className).toContain("!max-w-[90vw]");
  });

  it("应只渲染一个关闭按钮（自定义工具栏里的）", () => {
    render(
      <AttachmentLightbox
        attachment={mockAttachment}
        assetId="asset-1"
        onClose={() => {}}
      />,
    );

    // Count all buttons with close-related aria-labels
    const closeButtons = screen.getAllByRole("button", { name: /关闭|close/i });
    expect(closeButtons).toHaveLength(1);
  });
});
