import { describe, it, expect } from "vitest";
import { statusSortingFn } from "@/features/assets/list/assets-table-sorting";

describe("statusSortingFn", () => {
  it("应按 ASSET_STATUS_VALUES 生命周期顺序排序", () => {
    const rowA = { original: { status: "DISPOSED" } } as any;
    const rowB = { original: { status: "IDLE" } } as any;
    const rowC = { original: { status: "BROKEN" } } as any;

    expect(statusSortingFn(rowA, rowB, "status")).toBeGreaterThan(0);
    expect(statusSortingFn(rowB, rowC, "status")).toBeLessThan(0);
    expect(statusSortingFn(rowB, rowB, "status")).toBe(0);
  });

  it("未知状态应返 0 不抛错（防 schema 漂移）", () => {
    const rowA = { original: { status: "WEIRD_STATUS" as any } } as any;
    const rowB = { original: { status: "IDLE" } } as any;
    expect(statusSortingFn(rowA, rowB, "status")).toBe(0);
  });
});
