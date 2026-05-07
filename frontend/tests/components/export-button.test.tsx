import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { ExportButton } from "@/features/assets/list/export-button";
import type { AssetsSearch } from "@/features/assets/list/search-schema";

const baseSearch: AssetsSearch = {
  sort: "asset_code",
  page: 1,
  pageSize: 50,
};

describe("ExportButton", () => {
  it("renders a trigger button labeled 导出", () => {
    render(<ExportButton search={baseSearch} />);
    expect(
      screen.getByRole("button", { name: /导出/ }),
    ).toBeInTheDocument();
  });

  it("opens menu with Excel + CSV items on trigger click", async () => {
    const user = userEvent.setup();
    render(<ExportButton search={baseSearch} />);
    await user.click(screen.getByRole("button", { name: /导出/ }));
    expect(
      await screen.findByRole("menuitem", { name: /Excel/ }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("menuitem", { name: /CSV/ }),
    ).toBeInTheDocument();
  });

  it("Excel item renders as link with xlsx URL", async () => {
    const user = userEvent.setup();
    render(<ExportButton search={{ ...baseSearch, type: "uuid-1" }} />);
    await user.click(screen.getByRole("button", { name: /导出/ }));
    const excelItem = await screen.findByRole("menuitem", { name: /Excel/ });
    const anchor = excelItem.closest("a") ?? excelItem.querySelector("a");
    expect(anchor).toBeTruthy();
    expect(anchor!.getAttribute("href")).toContain("format=xlsx");
    expect(anchor!.getAttribute("href")).toContain("type_id=uuid-1");
  });

  it("CSV item renders as link with csv URL", async () => {
    const user = userEvent.setup();
    render(<ExportButton search={baseSearch} />);
    await user.click(screen.getByRole("button", { name: /导出/ }));
    const csvItem = await screen.findByRole("menuitem", { name: /CSV/ });
    const anchor = csvItem.closest("a") ?? csvItem.querySelector("a");
    expect(anchor).toBeTruthy();
    expect(anchor!.getAttribute("href")).toContain("format=csv");
  });
});
