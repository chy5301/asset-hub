import type { TransitionRead } from "@/features/assets/types";

/** 收集所有被 RETURN 关闭的 CHECKOUT id（即 RETURN.closes_transition_id 引用的 CHECKOUT.id 集合）。 */
export function getClosedCheckoutIds(transitions: TransitionRead[]): Set<string> {
  return new Set(
    transitions
      .filter((t) => t.kind === "RETURN" && t.closes_transition_id)
      .map((t) => t.closes_transition_id as string),
  );
}

/** 找当前 OPEN 的 CHECKOUT_*（kind 是 CHECKOUT_INTERNAL/EXTERNAL，且未被任何 RETURN 关闭）。
 *  状态机 INVARIANT：单台资产同时最多一个 OPEN CHECKOUT。 */
export function findOpenCheckout(transitions: TransitionRead[]): TransitionRead | null {
  const closedIds = getClosedCheckoutIds(transitions);
  return (
    transitions.find(
      (t) =>
        (t.kind === "CHECKOUT_INTERNAL" || t.kind === "CHECKOUT_EXTERNAL") &&
        !closedIds.has(t.id),
    ) ?? null
  );
}
