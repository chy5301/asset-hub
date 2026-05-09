import { test, expect } from "@playwright/test";
import { registerAsset } from "../helpers/register-asset";

// 实测 selector（来自 export-button.tsx）：
// - ExportButton：Button aria-label="导出"（触发 DropdownMenu）
// - DropdownMenuItem：文本 "Excel"（xlsx）和 "CSV"
// - 均为 <a href download> 原生下载链接

test.describe("06 · export-csv-xlsx", () => {
  test("seed 3 asset → 列表点导出 CSV + Excel", async ({ page }) => {
    registerAsset({ name: "Export A", sn: "PF-EXP-A" });
    registerAsset({ name: "Export B", sn: "PF-EXP-B" });
    registerAsset({ name: "Export C", sn: "PF-EXP-C" });

    await page.goto("/");

    // 打开导出下拉（aria-label="导出"）
    // 先下载 Excel（xlsx）
    const [downloadXlsx] = await Promise.all([
      page.waitForEvent("download"),
      (async () => {
        await page.getByRole("button", { name: "导出" }).click();
        await page.getByRole("menuitem", { name: "Excel" }).click();
      })(),
    ]);
    expect(downloadXlsx.suggestedFilename()).toMatch(/\.xlsx$/);

    // 再下载 CSV
    const [downloadCsv] = await Promise.all([
      page.waitForEvent("download"),
      (async () => {
        await page.getByRole("button", { name: "导出" }).click();
        await page.getByRole("menuitem", { name: "CSV" }).click();
      })(),
    ]);
    expect(downloadCsv.suggestedFilename()).toMatch(/\.csv$/);
  });
});
