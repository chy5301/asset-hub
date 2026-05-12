import { test, expect } from "@playwright/test";
import { registerAsset } from "../helpers/register-asset";
import { assertStatusChip } from "../helpers/assert-status";

// 实测 selector（来自 simple-transition-dialog.tsx / available-transitions.ts）：
// - 出现故障触发：MENU_ACTIONS[IN_USE] → "出现故障"（在 ⋯ DropdownMenu）
// - SimpleTransitionDialog(REPORT_BROKEN)：AlertDialogAction "确认出现故障"
// - BROKEN 主按钮：PRIMARY_ACTIONS[BROKEN] → "故障解除"
// - SimpleTransitionDialog(DISMISS)：AlertDialogAction "确认故障解除"
// - timeline：含 CHECKOUT_INTERNAL / REPORT_BROKEN / DISMISS 3 条

test.describe("08 · broken-dismiss", () => {
  test("BROKEN → DISMISS 自愈链", async ({ page }) => {
    const asset = registerAsset({ name: "X1 测试机 08", sn: "PF-E2E-08" });
    await page.goto(`/assets/${asset.id}`);
    await assertStatusChip(page, "IDLE");

    // 先派发（IN_USE 状态才能触发出现故障）
    await page.getByRole("button", { name: "派发" }).click();
    await page.getByLabel(/派发给/i).fill("张三");
    await page.getByRole("button", { name: "确认派发" }).click();
    await assertStatusChip(page, "IN_USE");

    // IN_USE 状态：触发"出现故障"（MENU_ACTIONS[IN_USE]）
    await page.getByRole("button", { name: "更多操作" }).click();
    await page.getByRole("menuitem", { name: /出现故障/i }).click();
    // ReportBrokenDialog：直接确认（holder 默认预填）
    await page.getByRole("button", { name: "确认出现故障" }).click();
    // 资产进入 BROKEN，StatusBadge 显示"故障"
    await assertStatusChip(page, "BROKEN");

    // BROKEN 状态：主按钮"故障解除"（PRIMARY_ACTIONS[BROKEN]）
    await page.getByRole("button", { name: "故障解除" }).click();
    // DismissDialog：确认解除
    await page.getByRole("button", { name: "确认故障解除" }).click();
    // 回到 IDLE
    await assertStatusChip(page, "IDLE");

    // timeline 应含派发、出现故障、故障解除三条记录
    await expect(page.getByText(/派发/i).first()).toBeVisible();
    await expect(page.getByText(/出现故障/i).first()).toBeVisible();
    await expect(page.getByText(/故障解除/i).first()).toBeVisible();
  });
});
