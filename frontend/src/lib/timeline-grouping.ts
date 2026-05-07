import { format, parseISO } from "date-fns";
import type { TransitionRead } from "@/features/assets/types";

export type GroupKind = "in-use" | "external";
export type GroupPosition = "start" | "middle" | "end";

export interface TransitionGroup {
  kind: GroupKind;
  position: GroupPosition;
}

export type GroupedTransition = TransitionRead & { group: TransitionGroup | null };

export interface MonthGroup<T = TransitionRead> {
  month: string;
  items: T[];
}

export function groupByMonth<T extends TransitionRead>(transitions: T[]): MonthGroup<T>[] {
  const buckets = new Map<string, T[]>();
  for (const t of transitions) {
    const month = format(parseISO(t.created_at), "yyyy-MM");
    const bucket = buckets.get(month) ?? [];
    bucket.push(t);
    buckets.set(month, bucket);
  }
  return Array.from(buckets.entries())
    .sort(([a], [b]) => b.localeCompare(a))
    .map(([month, items]) => ({ month, items }));
}

/** 给每条 transition 标记派出周期 group。
 *  输入按 created_at desc 排序（API 返回顺序）。
 *  算法：倒序遍历（数组尾部 = 最旧 → 数组头部 = 最新），按入队顺序配对 CHECKOUT_* ↔ RETURN。
 *  closes_transition_id 仅用于判断 CHECKOUT 是否 OPEN（构建 closedCheckoutIds Set），不用于直接配对——
 *  配对依赖状态机保证的"非嵌套"顺序单调性。 */
export function groupByCheckout(transitions: TransitionRead[]): GroupedTransition[] {
  const out: GroupedTransition[] = transitions.map((t) => ({ ...t, group: null }));

  const closedCheckoutIds = new Set(
    transitions
      .filter((t) => t.kind === "RETURN" && t.closes_transition_id)
      .map((t) => t.closes_transition_id as string),
  );

  // 找所有派出周期的 [start, end] 索引区间（数组索引）
  const cycles: { kind: GroupKind; startIdx: number; endIdx: number | null }[] = [];
  for (let i = transitions.length - 1; i >= 0; i--) {
    const t = transitions[i];
    if (t.kind === "CHECKOUT_INTERNAL" || t.kind === "CHECKOUT_EXTERNAL") {
      const kind: GroupKind = t.kind === "CHECKOUT_INTERNAL" ? "in-use" : "external";
      const isOpen = !closedCheckoutIds.has(t.id);
      cycles.push({ kind, startIdx: i, endIdx: isOpen ? null : -1 });
    } else if (t.kind === "RETURN" && t.closes_transition_id) {
      const cycle = cycles.find((c) => c.endIdx === -1);
      if (cycle) cycle.endIdx = i;
    }
  }

  for (const cycle of cycles) {
    out[cycle.startIdx].group = { kind: cycle.kind, position: "start" };

    if (cycle.endIdx !== null && cycle.endIdx >= 0) {
      out[cycle.endIdx].group = { kind: cycle.kind, position: "end" };
      // 中间（startIdx > i > endIdx，因 desc：startIdx 大 endIdx 小）
      for (let i = cycle.startIdx - 1; i > cycle.endIdx; i--) {
        if (out[i].group === null) out[i].group = { kind: cycle.kind, position: "middle" };
      }
    } else {
      // OPEN CHECKOUT：从 startIdx 向更新方向（i < startIdx）扫，所有未标记的中性卡都属于此周期
      for (let i = cycle.startIdx - 1; i >= 0; i--) {
        if (out[i].group === null) out[i].group = { kind: cycle.kind, position: "middle" };
      }
    }
  }

  return out;
}
