import { differenceInCalendarDays, parseISO } from "date-fns";
import type { AssetStatus } from "@/features/assets/types";

export type OverdueStatus = "pending" | "due-soon" | "overdue";

export interface OverdueResult {
  status: OverdueStatus;
  days: number;
}

export function calcOverdue(
  dueAt: string | null,
  assetStatus: AssetStatus,
  now: Date = new Date(),
): OverdueResult | null {
  if (assetStatus !== "IN_USE" || dueAt === null) return null;
  const due = parseISO(dueAt);
  const diff = differenceInCalendarDays(due, now);
  if (diff > 7) return { status: "pending", days: diff };
  if (diff >= 0) return { status: "due-soon", days: diff };
  return { status: "overdue", days: -diff };
}
