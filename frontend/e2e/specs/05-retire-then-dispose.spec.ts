import { test, expect } from "@playwright/test";
import { registerAsset } from "../helpers/register-asset";
import { assertStatusChip } from "../helpers/assert-status";

// 实测 selector（来自 dispose-alert-dialog.tsx / available-transitions.ts）：
// - DISPOSE 触发：MENU_ACTIONS[RETIRED] → "注销"（在 ⋯ DropdownMenu，label "注销…"）
// - DisposeAlertDialog：
//     confirm Input placeholder: `输入"注销"以解锁`（无 aria-label；用 placeholder 定位）
//     AlertDialogAction "确认注销"（disabled 直到 confirmText === "注销"）

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

    // 注销（MENU_ACTIONS[RETIRED] → "注销…"）
    await page.getByRole("button", { name: "更多操作" }).click();
    await page.getByRole("menuitem", { name: /注销/i }).click();

    // confirm Input（placeholder: `输入"注销"以解锁`）
    await page.getByPlaceholder(/输入.*注销.*解锁/i).fill("注销");

    // 提交按钮"确认注销"（填正确字后 enabled）
    await page.getByRole("button", { name: "确认注销" }).click();
    await assertStatusChip(page, "DISPOSED");

    // 验证终态：列表不见已注销资产
    await page.goto("/");
    await expect(page.getByText("X1 测试机 05")).not.toBeVisible();
  });
});
