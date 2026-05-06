import type { StatsRead } from "@/features/assets/types";

export type DashboardEmptyKind = "type" | "status" | "holder" | "idle";

/**
 * 按 spec §3.7: 4 种空态独立判定, length === 0 才空态;
 * 短列 (holder 5 行 / idle 6 行) 不视为空态——"少 = 好事".
 *
 * status 空态判定: empty record OR 所有计数都是 0.
 *
 * schema 允许 type_distribution / status_distribution / holder_ranking / idle_top
 * 为 nullable, 用 ?? 兜底视为 empty.
 */
export function detectDashboardEmpties(stats: StatsRead): DashboardEmptyKind[] {
  const empties: DashboardEmptyKind[] = [];

  if ((stats.type_distribution ?? []).length === 0) {
    empties.push("type");
  }

  const statusValues = Object.values(stats.status_distribution ?? {});
  if (statusValues.length === 0 || statusValues.every((c) => c === 0)) {
    empties.push("status");
  }

  if ((stats.holder_ranking ?? []).length === 0) {
    empties.push("holder");
  }

  if ((stats.idle_top ?? []).length === 0) {
    empties.push("idle");
  }

  return empties;
}
