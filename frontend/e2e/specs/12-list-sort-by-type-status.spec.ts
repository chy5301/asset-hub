import { test, expect } from "@playwright/test";

test.describe("资产列表 - 类型/状态列排序", () => {
  test("点击类型列表头触发 URL sort=type", async ({ page }) => {
    await page.goto("/");
    // 列 header 内部嵌 button（assets-table.tsx line 243-248），button selector 比 th 更稳
    await page.locator('thead th button:has-text("类型")').click();
    await expect(page).toHaveURL(/sort=type/);
  });

  test("点击状态列表头触发 URL sort=status", async ({ page }) => {
    await page.goto("/");
    // 同上：必须 click 内嵌 button 才能触发 TanStack getToggleSortingHandler
    await page.locator('thead th button:has-text("状态")').click();
    await expect(page).toHaveURL(/sort=status/);
    // 不断言 firstRow 内容 —— CI db 状态不可控（前 11 spec 残留数据状态分布无固定保证）
    // sortingFn 按 ASSET_STATUS_VALUES 下标排序的正确性由 unit test 覆盖
  });
});
