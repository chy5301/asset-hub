import { describe, expect, it } from "vitest";

import {
  type DashboardEmptyKind,
  detectDashboardEmpties,
} from "@/features/dashboard/empty-state";
import type { StatsRead } from "@/features/assets/types";

const fullStats: StatsRead = {
  type_distribution: [{ type_id: "x", type_name: "L", count: 5 }],
  status_distribution: { IDLE: 3 },
  holder_ranking: [{ holder: "张三", count: 5 }],
  idle_top: [
    {
      asset_id: "x",
      asset_code: "L-001",
      type_name: "L",
      current_location: null,
      idle_days: 30,
      idle_since: "2026-04-01T00:00:00Z",
    },
  ],
  summary: {
    total_assets: 5,
    registered_assets: 5,
    idle_count: 3,
    include_retired: false,
    include_disposed: false,
    generated_at: "2026-05-06T10:00:00Z",
  },
};

describe("detectDashboardEmpties", () => {
  it("returns no empties for full stats", () => {
    expect(detectDashboardEmpties(fullStats)).toEqual([]);
  });

  it("detects 'type' empty when type_distribution is []", () => {
    const e = detectDashboardEmpties({ ...fullStats, type_distribution: [] });
    expect(e).toContain<DashboardEmptyKind>("type");
  });

  it("detects 'status' empty when status_distribution is empty record", () => {
    const e = detectDashboardEmpties({ ...fullStats, status_distribution: {} });
    expect(e).toContain<DashboardEmptyKind>("status");
  });

  it("detects 'status' empty when all status counts are 0", () => {
    const e = detectDashboardEmpties({
      ...fullStats,
      status_distribution: { IDLE: 0, IN_USE: 0 },
    });
    expect(e).toContain<DashboardEmptyKind>("status");
  });

  it("detects 'holder' empty when holder_ranking is []", () => {
    const e = detectDashboardEmpties({ ...fullStats, holder_ranking: [] });
    expect(e).toContain<DashboardEmptyKind>("holder");
  });

  it("detects 'idle' empty when idle_top is []", () => {
    const e = detectDashboardEmpties({ ...fullStats, idle_top: [] });
    expect(e).toContain<DashboardEmptyKind>("idle");
  });

  it("does NOT mark short list as empty (holder 5 行不视为空态)", () => {
    const shortHolder = Array.from({ length: 5 }, (_, i) => ({
      holder: `H${i}`,
      count: i + 1,
    }));
    const e = detectDashboardEmpties({ ...fullStats, holder_ranking: shortHolder });
    expect(e).not.toContain<DashboardEmptyKind>("holder");
  });

  it("treats null/undefined fields as empty (schema 允许 nullable)", () => {
    const e = detectDashboardEmpties({
      ...fullStats,
      type_distribution: null,
      status_distribution: null,
      holder_ranking: null,
      idle_top: null,
    });
    expect(e).toEqual<DashboardEmptyKind[]>(["type", "status", "holder", "idle"]);
  });
});
