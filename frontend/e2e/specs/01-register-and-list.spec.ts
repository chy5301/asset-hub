import { test, expect } from "@playwright/test";
import { registerAsset } from "../helpers/register-asset";
import { assertStatusChip } from "../helpers/assert-status";

test.describe("01 · register-and-list", () => {
  test("CLI 登记资产 + UI 列表可见", async ({ page }) => {
    const asset = registerAsset({ name: "X1 测试机 01", sn: "PF-E2E-01" });
    expect(asset.id).toBeTruthy();
    expect(asset.status).toBe("IDLE");

    await page.goto("/");
    await expect(page.getByText("X1 测试机 01")).toBeVisible();
    await page.getByText("X1 测试机 01").click();

    // 详情页打开
    await expect(page.getByText("PF-E2E-01")).toBeVisible();
    await assertStatusChip(page, "IDLE");
  });
});
