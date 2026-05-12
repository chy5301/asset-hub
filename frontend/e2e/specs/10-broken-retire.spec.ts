import { test } from "@playwright/test";
import { registerAsset } from "../helpers/register-asset";
import { assertStatusChip } from "../helpers/assert-status";

// 实测 selector（来自 declare-unrepairable-alert-dialog.tsx / retire-alert-dialog.tsx / dispose-alert-dialog.tsx）：
// - IDLE → MAINTENANCE：MENU_ACTIONS[IDLE] → "送修…" → "确认送修"
// - MAINTENANCE → BROKEN：MENU_ACTIONS[MAINTENANCE] → "判定不可修复…" → "确认不可修复"
// - BROKEN → RETIRED：MENU_ACTIONS[BROKEN] → "退役…" → "确认退役"
// - RETIRED → DISPOSED：MENU_ACTIONS[RETIRED] → "注销…"
//     → placeholder "输入\"注销\"以解锁" → fill "注销" → "确认注销"
// 注意：DropdownMenuItem 自动附加 "…"，menuitem 用非锚定正则 /送修/i 匹配

test.describe("10 · broken-retire", () => {
  test("BROKEN → DECLARE_UNREPAIRABLE → RETIRE → DISPOSE 报废链", async ({ page }) => {
    const asset = registerAsset({ name: "X1 测试机 10", sn: "PF-E2E-10" });
    await page.goto(`/assets/${asset.id}`);
    await assertStatusChip(page, "IDLE");

    // IDLE → MAINTENANCE
    await page.getByRole("button", { name: "更多操作" }).click();
    await page.getByRole("menuitem", { name: /送修/i }).click();
    await page.getByRole("button", { name: "确认送修" }).click();
    await assertStatusChip(page, "MAINTENANCE");

    // MAINTENANCE → BROKEN（判定不可修复）
    await page.getByRole("button", { name: "更多操作" }).click();
    await page.getByRole("menuitem", { name: /判定不可修复/i }).click();
    await page.getByRole("button", { name: "确认不可修复" }).click();
    await assertStatusChip(page, "BROKEN");

    // BROKEN → RETIRED
    await page.getByRole("button", { name: "更多操作" }).click();
    await page.getByRole("menuitem", { name: /退役/i }).click();
    await page.getByRole("button", { name: "确认退役" }).click();
    await assertStatusChip(page, "RETIRED");

    // RETIRED → DISPOSED（注销，confirm phrase = "注销"）
    await page.getByRole("button", { name: "更多操作" }).click();
    await page.getByRole("menuitem", { name: /注销/i }).click();
    await page.getByPlaceholder(/输入.*注销.*解锁/i).fill("注销");
    await page.getByRole("button", { name: "确认注销" }).click();
    await assertStatusChip(page, "DISPOSED");
  });
});
