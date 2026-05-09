import { test, expect } from "@playwright/test";
import { registerAsset } from "../helpers/register-asset";
import { assertStatusChip } from "../helpers/assert-status";

// 实测 selector（来自 retire-alert-dialog.tsx / simple-transition-dialog.tsx / available-transitions.ts）：
// - 退役触发：MENU_ACTIONS[IDLE] → "退役"（在 ⋯ DropdownMenu，label "退役…"）
// - RetireAlertDialog：AlertDialogAction "确认退役"
// - 重新启用触发：PRIMARY_ACTIONS[RETIRED] → label "重新启用"（主按钮）
// - SimpleTransitionDialog(REINSTATE)：AlertDialogAction "确认重新启用"

test.describe("04 · retire-reinstate", () => {
  test("RETIRE → REINSTATE（验可复活）", async ({ page }) => {
    const asset = registerAsset({ name: "X1 测试机 04", sn: "PF-E2E-04" });
    await page.goto(`/assets/${asset.id}`);
    await assertStatusChip(page, "IDLE");

    // 打开 ⋯ 菜单，点"退役…"
    await page.getByRole("button", { name: "更多操作" }).click();
    await page.getByRole("menuitem", { name: /退役/i }).click();
    // 确认退役（AlertDialogAction text: "确认退役"）
    await page.getByRole("button", { name: "确认退役" }).click();
    await assertStatusChip(page, "RETIRED");

    // 默认列表不显示已退役资产
    await page.goto("/");
    await expect(page.getByText("X1 测试机 04")).not.toBeVisible();

    // 切回详情，重新启用（PRIMARY_ACTIONS[RETIRED] → "重新启用"）
    await page.goto(`/assets/${asset.id}`);
    await page.getByRole("button", { name: "重新启用" }).click();
    // 确认重新启用（AlertDialogAction text: "确认重新启用"）
    await page.getByRole("button", { name: "确认重新启用" }).click();
    await assertStatusChip(page, "IDLE");
  });
});
