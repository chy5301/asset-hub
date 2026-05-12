import { test } from "@playwright/test";
import { registerAsset } from "../helpers/register-asset";
import { assertStatusChip } from "../helpers/assert-status";

// 实测 selector（来自 report-broken-dialog.tsx / simple-transition-dialog.tsx / available-transitions.ts）：
// - 出现故障触发（IDLE）：MENU_ACTIONS[IDLE] → "出现故障…"（DropdownMenuItem 加 …）
// - ReportBrokenDialog：AlertDialogAction "确认标记"
// - BROKEN 菜单：MENU_ACTIONS[BROKEN] → "送修…"（DropdownMenuItem 加 …）
// - SimpleTransitionDialog(SEND_TO_MAINTENANCE)：AlertDialogAction "确认送修"
// - 维修完成：PRIMARY_ACTIONS[MAINTENANCE] → "维修完成"
// - SimpleTransitionDialog(RECOVER_FROM_MAINTENANCE)：AlertDialogAction "确认维修完成"

test.describe("09 · broken-maintenance", () => {
  test("BROKEN → SEND_TO_MAINTENANCE → RECOVER", async ({ page }) => {
    const asset = registerAsset({ name: "X1 测试机 09", sn: "PF-E2E-09" });
    await page.goto(`/assets/${asset.id}`);
    await assertStatusChip(page, "IDLE");

    // IDLE → BROKEN（直接从 IDLE 触发出现故障）
    await page.getByRole("button", { name: "更多操作" }).click();
    await page.getByRole("menuitem", { name: /出现故障/i }).click();
    await page.getByRole("button", { name: "确认标记" }).click();
    await assertStatusChip(page, "BROKEN");

    // BROKEN → MAINTENANCE（MENU_ACTIONS[BROKEN] → "送修…"）
    await page.getByRole("button", { name: "更多操作" }).click();
    await page.getByRole("menuitem", { name: /送修/i }).click();
    // SimpleTransitionDialog(SEND_TO_MAINTENANCE)：AlertDialogAction "确认送修"
    await page.getByRole("button", { name: "确认送修" }).click();
    await assertStatusChip(page, "MAINTENANCE");

    // MAINTENANCE → IDLE（PRIMARY_ACTIONS[MAINTENANCE] → "维修完成"）
    await page.getByRole("button", { name: "维修完成" }).click();
    await page.getByRole("button", { name: "确认维修完成" }).click();
    await assertStatusChip(page, "IDLE");
  });
});
