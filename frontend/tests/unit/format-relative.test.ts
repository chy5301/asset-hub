import { describe, expect, it } from "vitest";
import { formatRelative } from "@/lib/date";

const NOW = new Date("2026-05-07T10:00:00Z");

describe("formatRelative", () => {
  it("当天 → 今天", () => {
    expect(formatRelative("2026-05-07T08:00:00Z", NOW)).toBe("今天");
  });

  it("1 天前 → 昨天", () => {
    expect(formatRelative("2026-05-06T08:00:00Z", NOW)).toBe("昨天");
  });

  it("N 天前", () => {
    expect(formatRelative("2026-05-02T08:00:00Z", NOW)).toBe("5 天前");
    expect(formatRelative("2026-04-07T08:00:00Z", NOW)).toBe("30 天前");
  });

  it("跨年仍用天", () => {
    expect(formatRelative("2025-05-07T08:00:00Z", NOW)).toBe("365 天前");
  });

  it("未来日期（边界异常）→ 今天", () => {
    // 后端不应给未来 created_at；防御性返今天
    expect(formatRelative("2026-05-10T08:00:00Z", NOW)).toBe("今天");
  });

  it("跨本地午夜 1 小时 → 昨天（按本地日历日，不按 ms）", () => {
    // 用 Date 构造器的本地时区参数：iso 本地 5/6 23:30，now 本地 5/7 00:30
    const yesterdayLocal = new Date(2026, 4, 6, 23, 30, 0).toISOString();
    const todayLocal = new Date(2026, 4, 7, 0, 30, 0);
    expect(formatRelative(yesterdayLocal, todayLocal)).toBe("昨天");
  });
});
