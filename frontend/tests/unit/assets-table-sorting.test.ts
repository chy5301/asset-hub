import { describe, it, expect } from "vitest";
import type { Row } from "@tanstack/react-table";
import { statusSortingFn } from "@/features/assets/list/assets-table-sorting";
import type { AssetRow } from "@/features/assets/list/assets-table";
import type { AssetStatus } from "@/features/assets/status-labels";

function makeRow(status: AssetStatus): Row<AssetRow> {
  return { original: { status } } as unknown as Row<AssetRow>;
}

describe("statusSortingFn", () => {
  it("应按 ASSET_STATUS_VALUES 生命周期顺序排序", () => {
    const rowA = makeRow("DISPOSED");
    const rowB = makeRow("IDLE");
    const rowC = makeRow("BROKEN");

    expect(statusSortingFn(rowA, rowB, "status")).toBeGreaterThan(0);
    expect(statusSortingFn(rowB, rowC, "status")).toBeLessThan(0);
    expect(statusSortingFn(rowB, rowB, "status")).toBe(0);
  });

  it("未知状态应返 0 不抛错（防 schema 漂移）", () => {
    const rowA = { original: { status: "WEIRD_STATUS" as unknown as AssetStatus } } as unknown as Row<AssetRow>;
    const rowB = makeRow("IDLE");
    expect(statusSortingFn(rowA, rowB, "status")).toBe(0);
  });
});
