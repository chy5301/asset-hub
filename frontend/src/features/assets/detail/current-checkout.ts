import type { components } from "@/api/generated/schema";

type CheckoutRead = components["schemas"]["CheckoutRead"];

/**
 * 从流转 history 中找出"当前进行中"的派发记录。
 * 不变量：service 层保证同一资产同一时刻最多 1 条 returned_at === null。
 */
export function deriveCurrentCheckout(
  history: CheckoutRead[] | undefined,
): CheckoutRead | null {
  if (!history) return null;
  return history.find((c) => c.returned_at === null) ?? null;
}
