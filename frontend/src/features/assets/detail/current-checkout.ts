import type { components } from "@/api/generated/schema";

type CheckoutRead = components["schemas"]["CheckoutRead"];

/**
 * 用 asset.current_checkout_id 在 history 中定位当前派发记录。
 *
 * 后端 AssetRead 已直接暴露 current_checkout_id（M2c-3）；前端不再依赖
 * "history 中 returned_at === null" 这个 service 层不变量，避免泄漏。
 */
export function deriveCurrentCheckout(
  history: CheckoutRead[] | undefined,
  currentCheckoutId: string | null | undefined,
): CheckoutRead | null {
  if (!history || !currentCheckoutId) return null;
  return history.find((c) => c.id === currentCheckoutId) ?? null;
}
