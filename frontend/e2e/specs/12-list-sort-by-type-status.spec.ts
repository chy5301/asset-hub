import { test, expect } from "@playwright/test";

test.describe("资产列表 - 类型/状态列排序", () => {
  test("点击类型列表头应触发字典序升序", async ({ page }) => {
    await page.goto("/");
    const typeHeader = page.getByRole("columnheader", { name: /类型/ });
    await typeHeader.click();
    await expect(page).toHaveURL(/sort=type/);
  });

  test("点击状态列表头应按生命周期顺序排序，IDLE 排第一", async ({ page }) => {
    await page.goto("/");
    const statusHeader = page.getByRole("columnheader", { name: /状态/ });
    await statusHeader.click();
    await expect(page).toHaveURL(/sort=status/);
    const firstRow = page.locator("tbody tr").first();
    await expect(firstRow).toContainText("闲置中");
  });
});
