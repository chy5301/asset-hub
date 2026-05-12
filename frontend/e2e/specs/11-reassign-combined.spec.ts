import { test, expect } from "@playwright/test";
import { registerAsset } from "../helpers/register-asset";
import { assertStatusChip } from "../helpers/assert-status";

// 实测 selector（来自 reassign-dialog.tsx / available-transitions.ts）：
// - REASSIGN 触发：MENU_ACTIONS[IN_USE/IDLE/...] → "重新分配…"（DropdownMenuItem 加 …）
// - ReassignDialog 字段：FormLabel "持有人"、FormLabel "位置"
// - 提交：AlertDialogAction "确认"
// - timeline：formatLine REASSIGN 显示 "持有人 X → Y · 位置 A → B"
//
// NOTE: ReassignDialog 已修复 AlertDialogAction 沉默失败问题（e.preventDefault() + 手动 onOpenChange(false)）

test.describe("11 · reassign-combined", () => {
  test("REASSIGN 同时改 holder + location 一步完成", async ({ page }) => {
    const asset = registerAsset({ name: "X1 测试机 11", sn: "PF-E2E-11" });
    await page.goto(`/assets/${asset.id}`);
    await assertStatusChip(page, "IDLE");

    // 先派发给张三，位置 L1
    await page.getByRole("button", { name: "派发" }).click();
    await page.getByLabel(/派发给/i).fill("张三");
    await page.getByLabel(/位置（可选）/i).first().fill("L1");
    await page.getByRole("button", { name: "确认派发" }).click();
    await assertStatusChip(page, "IN_USE");

    // IN_USE 状态：触发"重新分配"（MENU_ACTIONS[IN_USE]）
    await page.getByRole("button", { name: "更多操作" }).click();
    await page.getByRole("menuitem", { name: /重新分配/i }).click();

    // ReassignDialog 对话框打开
    const dialog = page.getByRole("alertdialog");
    await expect(dialog).toBeVisible();

    // 获取 dialog 内的 input（to_holder, to_location）
    await dialog.locator("input").nth(0).fill("李四");
    await dialog.locator("input").nth(1).fill("L2");

    // 提交（AlertDialogAction text: "确认"）
    await dialog.getByRole("button", { name: "确认" }).click();

    // 等待 toast "已重新分配" 出现（证明 mutation 成功）
    await expect(page.getByText("已重新分配")).toBeVisible({ timeout: 8000 });

    // 状态保持 IN_USE（REASSIGN 不改状态）
    await assertStatusChip(page, "IN_USE");

    // timeline 应有 REASSIGN 卡（等待 React Query 刷新）
    await expect(page.getByText(/重新分配/i).first()).toBeVisible({ timeout: 8000 });
  });
});
