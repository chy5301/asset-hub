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
  BROKEN:      [{ kind: "DISMISS", label: "故障解除" }],
  RETIRED:     [{ kind: "REINSTATE", label: "重新启用" }],
  DISPOSED:    [],
};

/** ⋯ 菜单可见项（按 status 过滤）。DISPOSED 全只读，菜单为空。 */
export const MENU_ACTIONS: Record<AssetStatus, MenuAction[]> = {
  IDLE: [
    { kind: "SEND_TO_MAINTENANCE", label: "送修" },
    { kind: "REPORT_BROKEN",       label: "出现故障" },
    { kind: "REASSIGN",            label: "重新分配" },
    { kind: "RETIRE",              label: "退役" },
  ],
  IN_USE: [
    { kind: "REPORT_BROKEN",       label: "出现故障" },
    { kind: "REASSIGN",            label: "重新分配" },
  ],
  MAINTENANCE: [
    { kind: "DECLARE_UNREPAIRABLE", label: "判定不可修复" },
    { kind: "REASSIGN",             label: "重新分配" },
    { kind: "RETIRE",               label: "退役" },
    { kind: "DISPOSE",              label: "注销" },
  ],
  BROKEN: [
    { kind: "SEND_TO_MAINTENANCE",  label: "送修" },
    { kind: "DECLARE_UNREPAIRABLE", label: "判定不可修复" },
    { kind: "REASSIGN",             label: "重新分配" },
    { kind: "RETIRE",               label: "退役" },
    { kind: "DISPOSE",              label: "注销" },
  ],
  RETIRED: [
    { kind: "REASSIGN",            label: "重新分配" },
    { kind: "DISPOSE",             label: "注销" },
  ],
  DISPOSED: [],
};
