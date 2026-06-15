import { test, expect } from "@playwright/test";
import { registerAsset } from "../helpers/register-asset";

// issue #39 回归：编辑页中选项数>4（渲染为 Select 下拉）的 enum 自定义字段，
// 必须回显该资产已保存的现有值，而非停在占位符「请选择」。
// 该 bug 只在真实浏览器复现（jsdom 协调会抹平时序），故守在 e2e 层。
test.describe("13 · edit-select-enum-reflect", () => {
  test("编辑页 Select 渲染的 enum 字段回显已存值", async ({ page }) => {
    // form_factor 有 5 个选项（>4）→ 走 Select；登记时存「塔式」
    const asset = registerAsset({
      name: "WS 回显测试 13",
      sn: "WS-E2E-13",
      custom: { form_factor: "塔式" },
      typeIdFile: "ws-type-id.txt",
    });

    await page.goto(`/assets/${asset.id}/edit`);

    const trigger = page.locator("#field-form_factor");
    const valueText = trigger.locator('[data-slot="select-value"]');
    // 触发器须显示已存值「塔式」，而非占位符
    await expect(valueText).toHaveText("塔式");
    await expect(trigger).not.toHaveAttribute("data-placeholder", "");

    // 用户改选另一项后：触发器须更新，且焦点须回到触发器（key 重挂载会丢焦点，
    // onValueChange 里手动恢复 —— 守住该修复，防止键盘焦点连续性回归）
    await trigger.click();
    await page.getByRole("option", { name: "机架" }).click();
    await expect(valueText).toHaveText("机架");
    await expect(trigger).toBeFocused();
  });
});
