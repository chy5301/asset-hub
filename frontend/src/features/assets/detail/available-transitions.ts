import type { TransitionKind } from "@/features/assets/types";
import type { AssetStatus } from "@/features/assets/status-labels";

/** 派发/出借两 kind 的窄类型，CheckoutDialog / 列表行尾菜单 / asset-header 共用。 */
export type CheckoutKind = Extract<TransitionKind, "CHECKOUT_INTERNAL" | "CHECKOUT_EXTERNAL">;

export interface PrimaryAction {
  kind: TransitionKind;
  label: string;
}

export interface MenuAction {
  kind: TransitionKind;
  label: string;
}

/** 详情页主按钮（按 status 决定主操作；可能多个并列）。DISPOSED 无主按钮。 */
export const PRIMARY_ACTIONS: Record<AssetStatus, PrimaryAction[]> = {
  IDLE:        [
    { kind: "CHECKOUT_INTERNAL", label: "派发" },
    { kind: "CHECKOUT_EXTERNAL", label: "出借" },
  ],
  IN_USE:      [{ kind: "RETURN", label: "归还" }],
  MAINTENANCE: [{ kind: "RECOVER_FROM_MAINTENANCE", label: "维修完成" }],
  RETIRED:     [{ kind: "REINSTATE", label: "重新启用" }],
  DISPOSED:    [],
};

/** ⋯ 菜单可见项（按 status 过滤）。DISPOSED 全只读，菜单为空。 */
export const MENU_ACTIONS: Record<AssetStatus, MenuAction[]> = {
  IDLE: [
    { kind: "SEND_TO_MAINTENANCE", label: "送修" },
    { kind: "RETIRE",              label: "退役" },
    { kind: "RELOCATE",            label: "变更位置" },
    { kind: "TRANSFER_HOLDER",     label: "变更保管人" },
  ],
  IN_USE: [
    { kind: "RELOCATE",            label: "变更位置" },
    { kind: "TRANSFER_HOLDER",     label: "变更保管人" },
  ],
  MAINTENANCE: [
    { kind: "RETIRE",              label: "退役" },
    { kind: "DISPOSE",             label: "处置" },
    { kind: "RELOCATE",            label: "变更位置" },
    { kind: "TRANSFER_HOLDER",     label: "变更保管人" },
  ],
  RETIRED: [
    { kind: "DISPOSE",             label: "处置" },
    { kind: "RELOCATE",            label: "变更位置" },
    { kind: "TRANSFER_HOLDER",     label: "变更保管人" },
  ],
  DISPOSED: [],
};
