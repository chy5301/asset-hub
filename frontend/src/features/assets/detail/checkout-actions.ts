// frontend/src/features/assets/detail/checkout-actions.ts

/**
 * 派发 / 归还动词常量。
 *
 * M2c-2 只支持单一派出类型（组内派发），因此 CTA 文字是字符串常量。
 *
 * M3 扩展"向外出借"（见 spec §10.1）时，CHECKOUT_VERB 升级为：
 *   export const CHECKOUT_TYPES = [
 *     { key: 'internal', verb: '派发', dialogTitle: '组内派发', icon: Users },
 *     { key: 'external', verb: '借出', dialogTitle: '向外出借', icon: ExternalLink },
 *   ] as const
 * CtaButton 同步从 <Button> 升级为 split-button。
 */
export const CHECKOUT_VERB = "派发";
export const RETURN_VERB = "归还";

/** Dialog 标题（与 verb 一致，但分离是为了 M3 扩展时独立变化） */
export const CHECKOUT_DIALOG_TITLE = "派发资产";
export const RETURN_DIALOG_TITLE = "归还资产";

/** mutation pending 时的按钮文字 */
export const CHECKOUT_PENDING_TEXT = "派发中…";
export const RETURN_PENDING_TEXT = "归还中…";
export const DELETE_ATTACHMENT_PENDING_TEXT = "删除中…";
