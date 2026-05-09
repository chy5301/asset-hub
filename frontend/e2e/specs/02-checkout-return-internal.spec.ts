import { test, expect } from "@playwright/test";
import { registerAsset } from "../helpers/register-asset";
import { assertStatusChip } from "../helpers/assert-status";

// 实测 selector（来自 checkout-dialog.tsx / return-dialog.tsx / available-transitions.ts）：
// - 触发按钮：PRIMARY_ACTIONS[IDLE] → label "派发"（Button text）
// - CheckoutDialog 表单字段：FormLabel "派发给 *"（to_holder），"位置（可选）"（to_location）
// - 提交按钮：Button text "确认派发"
// - 归还触发：PRIMARY_ACTIONS[IN_USE] → label "归还"
// - ReturnDialog 表单字段：FormLabel "归还给（可选，留空表示无人值守）"（to_holder），"归还位置（可选）"（to_location）
// - 提交按钮：Button text "确认归还"

test.describe("02 · checkout-return-internal", () => {
  test("CHECKOUT_INTERNAL → RETURN 闭环", async ({ page }) => {
    const asset = registerAsset({ name: "X1 测试机 02", sn: "PF-E2E-02" });
    await page.goto(`/assets/${asset.id}`);
    await assertStatusChip(page, "IDLE");

    // 点主按钮"派发"（IDLE 状态的 primary action）
    await page.getByRole("button", { name: "派发" }).click();
    // 填写 to_holder（FormLabel: "派发给 *"）
    await page.getByLabel(/派发给/i).fill("张三");
    // 填写位置（FormLabel: "位置（可选）"）
    await page.getByLabel(/位置（可选）/i).first().fill("北京办公室");
    // 提交（Button text: "确认派发"）
    await page.getByRole("button", { name: "确认派发" }).click();

    // status 变 IN_USE
    await assertStatusChip(page, "IN_USE");

    // 归还（IN_USE 状态的 primary action，Button text "归还"）
    await page.getByRole("button", { name: "归还" }).click();
    // 填写归还给（FormLabel: "归还给（可选，留空表示无人值守）"）
    await page.getByLabel(/归还给/i).fill("李四");
    // 归还位置（FormLabel: "归还位置（可选）"）
    await page.getByLabel(/归还位置/i).fill("上海仓库");
    // 提交（Button text: "确认归还"）
    await page.getByRole("button", { name: "确认归还" }).click();

    await assertStatusChip(page, "IDLE");

    // timeline 应有派发 + 归还两条记录（显示 toast 或 timeline 文案）
    await expect(page.getByText(/派发/i).first()).toBeVisible();
    await expect(page.getByText(/归还/i).first()).toBeVisible();
  });
});
