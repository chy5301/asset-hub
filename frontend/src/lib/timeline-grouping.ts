import { format, parseISO } from "date-fns";
import type { TransitionRead } from "@/features/assets/types";
import { getClosedCheckoutIds } from "@/lib/transition-state";

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

/** 给每条 transition 标记派出周期 group。输入按 created_at desc 排序（API 返回顺序）。
 *
 *  CHECKOUT_* / RETURN 配对靠 RETURN.closes_transition_id 显式 lookup（非依赖顺序单调性），
 *  防止历史数据异常时配对错误。OPEN CHECKOUT 向更新方向延伸 middle 标记。 */
export function groupByCheckout(transitions: TransitionRead[]): GroupedTransition[] {
  const out: GroupedTransition[] = transitions.map((t) => ({ ...t, group: null }));

  const closedCheckoutIds = getClosedCheckoutIds(transitions);

  // CHECKOUT.id → 配对的 RETURN 索引（O(N) 预建，避免内层 findIndex）
  const returnIdxByCheckoutId = new Map<string, number>();
  for (let i = 0; i < transitions.length; i++) {
    const t = transitions[i];
    if (t.kind === "RETURN" && t.closes_transition_id) {
      returnIdxByCheckoutId.set(t.closes_transition_id, i);
    }
  }

  // 倒序扫（最旧 → 最新），每遇 CHECKOUT_* 起新周期
  for (let i = transitions.length - 1; i >= 0; i--) {
    const t = transitions[i];
    if (t.kind !== "CHECKOUT_INTERNAL" && t.kind !== "CHECKOUT_EXTERNAL") continue;

    const kind: GroupKind = t.kind === "CHECKOUT_INTERNAL" ? "in-use" : "external";
    out[i].group = { kind, position: "start" };

    if (closedCheckoutIds.has(t.id)) {
      // 已配对的 RETURN（必定在更新方向：索引 < startIdx，因数组 desc）
      const endIdx = returnIdxByCheckoutId.get(t.id);
      if (endIdx === undefined) continue; // 防御：closedIds 与 map 理论一致
      out[endIdx].group = { kind, position: "end" };
      for (let j = i - 1; j > endIdx; j--) {
        if (out[j].group === null) out[j].group = { kind, position: "middle" };
      }
    } else {
      // OPEN CHECKOUT：向更新方向扫到列表头，所有未标记的中性卡都属于此周期
      for (let j = i - 1; j >= 0; j--) {
        if (out[j].group === null) out[j].group = { kind, position: "middle" };
      }
    }
  }

  return out;
}
