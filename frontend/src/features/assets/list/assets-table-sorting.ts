import type { Row } from "@tanstack/react-table";

import { ASSET_STATUS_VALUES } from "./search-schema";
import type { AssetRow } from "@/features/assets/list/assets-table";

/**
 * status 列按 ASSET_STATUS_VALUES 数组下标排序（生命周期顺序），
 * 未知状态返 0 防 schema 漂移导致排序抛错。
 */
export function statusSortingFn(
  rowA: Row<AssetRow>,
  rowB: Row<AssetRow>,
): number {
  const a = ASSET_STATUS_VALUES.indexOf(rowA.original.status as never);
  const b = ASSET_STATUS_VALUES.indexOf(rowB.original.status as never);
  if (a < 0 || b < 0) return 0;
  return a - b;
}
