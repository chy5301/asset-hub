import { test } from "@playwright/test";
import { registerAsset } from "../helpers/register-asset";
import { assertStatusChip } from "../helpers/assert-status";

// 实测 selector（来自 simple-transition-dialog.tsx / available-transitions.ts）：
// - 送修触发：MENU_ACTIONS[IDLE] → "送修"（在 ⋯ DropdownMenu 里，label "送修…"）
// - SimpleTransitionDialog（AlertDialog）：AlertDialogAction "确认送修"
// - 维修完成触发：PRIMARY_ACTIONS[MAINTENANCE] → label "维修完成"（Button text）
// - AlertDialogAction "确认维修完成"

test.describe("03 · maintenance-cycle", () => {
  test("SEND_TO_MAINTENANCE → RECOVER_FROM_MAINTENANCE", async ({ page }) => {
    const asset = registerAsset({ name: "X1 测试机 03", sn: "PF-E2E-03" });
    await page.goto(`/assets/${asset.id}`);
    await assertStatusChip(page, "IDLE");

    // 打开 ⋯ 更多操作菜单（Button aria-label="更多操作"），点"送修…"
    await page.getByRole("button", { name: "更多操作" }).click();
    await page.getByRole("menuitem", { name: /送修/i }).click();
    // 确认送修（AlertDialogAction text: "确认送修"）
    await page.getByRole("button", { name: "确认送修" }).click();
    await assertStatusChip(page, "MAINTENANCE");

    // 维修完成（PRIMARY_ACTIONS[MAINTENANCE] → "维修完成"，为主按钮）
    await page.getByRole("button", { name: "维修完成" }).click();
    // 确认维修完成（AlertDialogAction text: "确认维修完成"）
    await page.getByRole("button", { name: "确认维修完成" }).click();
    await assertStatusChip(page, "IDLE");
  });
});
