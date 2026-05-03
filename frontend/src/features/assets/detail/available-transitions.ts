import type { AssetStatus } from "@/features/assets/status-labels";
import type { components } from "@/api/generated/schema";

type TransitionKind = components["schemas"]["TransitionKind"];

export interface PrimaryAction {
  kind: TransitionKind | "DISPATCH_GROUP";  // DISPATCH_GROUP 表示 CHECKOUT_INTERNAL/EXTERNAL 选择
  label: string;
}

export interface MenuAction {
  kind: TransitionKind;
  label: string;
}

/** 详情页主按钮（按 status 决定唯一主操作）。DISPOSED 无主按钮。 */
export const PRIMARY_ACTION: Record<AssetStatus, PrimaryAction | null> = {
  IDLE:        { kind: "DISPATCH_GROUP",        label: "派发" },
  IN_USE:      { kind: "RETURN",                label: "归还" },
  MAINTENANCE: { kind: "RECOVER_FROM_MAINTENANCE", label: "维修完成" },
  RETIRED:     { kind: "REINSTATE",             label: "重新启用" },
  DISPOSED:    null,
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
