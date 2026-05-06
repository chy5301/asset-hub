import { describe, expect, it } from "vitest";
import { typeIdToChartSlot, typeIdToChartTokenVar } from "@/features/dashboard/charts/chart-token";

describe("typeIdToChartSlot", () => {
  it("returns slot 1..6", () => {
    const slot = typeIdToChartSlot("a-1234");
    expect(slot).toBeGreaterThanOrEqual(1);
    expect(slot).toBeLessThanOrEqual(6);
  });

  it("is stable for same input", () => {
    const slot1 = typeIdToChartSlot("uuid-foo");
    const slot2 = typeIdToChartSlot("uuid-foo");
    expect(slot1).toBe(slot2);
  });

  it("empty string returns slot 1 (deterministic fallback)", () => {
    expect(typeIdToChartSlot("")).toBe(1);
  });
});

describe("typeIdToChartTokenVar", () => {
  it("returns css var name in chart-[1-6] range", () => {
    const v = typeIdToChartTokenVar("uuid-foo");
    expect(v).toMatch(/^var\(--chart-[1-6]\)$/);
  });
});
