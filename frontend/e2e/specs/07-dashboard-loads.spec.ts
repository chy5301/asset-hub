import { test, expect } from "@playwright/test";
import { registerAsset } from "../helpers/register-asset";

// 实测 dashboard 图表标题（来自 dashboard/charts/*.tsx）：
// - IdleTopBarChart:        h2 "闲置时长 Top 10"
// - TypeDistributionChart:  h2 "类型分布"
// - StatusDistributionChart: h2 "状态分布"
// - HolderLeaderboard:      h2 "保管人持有"

test.describe("07 · dashboard-loads", () => {
  test("/dashboard 4 张图都渲染", async ({ page }) => {
    // seed 至少 1 个资产，避免空盘面
    registerAsset({ name: "Dash A", sn: "PF-DASH-A" });

    await page.goto("/dashboard");

    // 4 张图标题
    await expect(page.getByText("闲置时长 Top 10")).toBeVisible();
    await expect(page.getByText("类型分布")).toBeVisible();
    await expect(page.getByText("状态分布")).toBeVisible();
    await expect(page.getByText("保管人持有")).toBeVisible();

    // 状态分布应显示新文案（seeded 资产为 IDLE → 闲置中）
    await expect(page.getByText(/闲置中/i)).toBeVisible();
  });
});
