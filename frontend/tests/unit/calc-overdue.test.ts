import { describe, expect, it } from "vitest";
import { calcOverdue } from "@/lib/overdue";

const NOW = new Date("2026-05-07T10:00:00Z");

describe("calcOverdue", () => {
  it("status !== IN_USE 返 null", () => {
    expect(calcOverdue("2026-05-10", "IDLE", NOW)).toBeNull();
    expect(calcOverdue("2026-05-10", "MAINTENANCE", NOW)).toBeNull();
    expect(calcOverdue("2026-05-10", "RETIRED", NOW)).toBeNull();
    expect(calcOverdue("2026-05-10", "DISPOSED", NOW)).toBeNull();
  });

  it("dueAt === null 返 null", () => {
    expect(calcOverdue(null, "IN_USE", NOW)).toBeNull();
  });

  it("now < dueAt - 7d → pending", () => {
    expect(calcOverdue("2026-05-20", "IN_USE", NOW)).toEqual({
      status: "pending",
      days: 13,
    });
  });

  it("边界：now === dueAt - 7d → due-soon", () => {
    expect(calcOverdue("2026-05-14", "IN_USE", NOW)).toEqual({
      status: "due-soon",
      days: 7,
    });
  });

  it("边界：now === dueAt → due-soon", () => {
    expect(calcOverdue("2026-05-07", "IN_USE", NOW)).toEqual({
      status: "due-soon",
      days: 0,
    });
  });

  it("now > dueAt → overdue (取绝对值)", () => {
    expect(calcOverdue("2026-04-29", "IN_USE", NOW)).toEqual({
      status: "overdue",
      days: 8,
    });
  });

  it("跨年逾期", () => {
    const lastYear = new Date("2025-12-15T10:00:00Z");
    expect(calcOverdue("2025-12-01", "IN_USE", lastYear)).toEqual({
      status: "overdue",
      days: 14,
    });
  });
});
