import { expect, type Page } from "@playwright/test";

import {
  STATUS_META,
  type AssetStatus,
} from "../../src/features/assets/status-labels";

/**
 * 在资产详情页验证 status chip 文案与 5 态 SoT 对齐。
 * 直接 import STATUS_META 避免在 e2e 维护重复 label 字典。
 */
export async function assertStatusChip(page: Page, status: AssetStatus) {
  const expected = STATUS_META[status].label;
  await expect(page.getByText(expected, { exact: true }).first()).toBeVisible();
}
