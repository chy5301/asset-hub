import { test, expect } from "@playwright/test";
import { registerAsset } from "../helpers/register-asset";
import { assertStatusChip } from "../helpers/assert-status";

// 实测 selector（来自 dispose-alert-dialog.tsx / available-transitions.ts）：
// - DISPOSE 触发：MENU_ACTIONS[RETIRED] → "处置"（在 ⋯ DropdownMenu，label "处置…"）
// - DisposeAlertDialog：
//     confirm Input placeholder: `输入"处置"以解锁`（无 aria-label；用 placeholder 定位）
//     AlertDialogAction "确认处置"（disabled 直到 confirmText === "处置"）

test.describe("05 · retire-then-dispose", () => {
  test("RETIRE → DISPOSE（终态锁）", async ({ page }) => {
    const asset = registerAsset({ name: "X1 测试机 05", sn: "PF-E2E-05" });
    await page.goto(`/assets/${asset.id}`);
    await assertStatusChip(page, "IDLE");

    // 必须先退役
    await page.getByRole("button", { name: "更多操作" }).click();
    await page.getByRole("menuitem", { name: /退役/i }).click();
    await page.getByRole("button", { name: "确认退役" }).click();
    await assertStatusChip(page, "RETIRED");

    // 处置（MENU_ACTIONS[RETIRED] → "处置…"）
    await page.getByRole("button", { name: "更多操作" }).click();
    await page.getByRole("menuitem", { name: /处置/i }).click();

    // confirm Input（placeholder: `输入"处置"以解锁`）
    await page.getByPlaceholder(/输入.*处置.*解锁/i).fill("处置");

    // 提交按钮"确认处置"（填正确字后 enabled）
    await page.getByRole("button", { name: "确认处置" }).click();
    await assertStatusChip(page, "DISPOSED");

    // 验证终态：列表不见已处置资产
    await page.goto("/");
    await expect(page.getByText("X1 测试机 05")).not.toBeVisible();
  });
});
