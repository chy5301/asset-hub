import { expect, type Page } from "@playwright/test";

/**
 * 与 frontend/src/features/assets/status-labels.ts 的 STATUS_META 保持同步。
 * 不强匹配 chip 颜色（视觉测试归 vitest component 层）。
 */
const STATUS_LABELS: Record<string, string> = {
  IDLE: "闲置中",
  IN_USE: "使用中",
  MAINTENANCE: "维修中",
  RETIRED: "已退役",
  DISPOSED: "已处置",
};

/**
 * 在资产详情页验证 status chip 文案与新 5 态对齐。
 */
export async function assertStatusChip(
  page: Page,
  status: keyof typeof STATUS_LABELS,
) {
  const expected = STATUS_LABELS[status];
  await expect(page.getByText(expected, { exact: true }).first()).toBeVisible();
}
