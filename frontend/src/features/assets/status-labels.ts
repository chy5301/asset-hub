import { Archive, Circle, CircleDot, Moon, Wrench, type LucideIcon } from "lucide-react";

export type AssetStatus = "IN_USE" | "IDLE" | "MAINTENANCE" | "RETIRED" | "DISPOSED";

export interface StatusMeta {
  label: string;
  bgVar: string;
  fgVar: string;
  Icon: LucideIcon;
}

export const STATUS_META: Record<AssetStatus, StatusMeta> = {
  IN_USE: {
    label: "使用中",
    bgVar: "--status-in-use",
    fgVar: "--status-in-use-fg",
    Icon: CircleDot,
  },
  IDLE: {
    label: "闲置中",
    bgVar: "--status-idle",
    fgVar: "--status-idle-fg",
    Icon: Circle,
  },
  MAINTENANCE: {
    label: "维修中",
    bgVar: "--status-maintenance",
    fgVar: "--status-maintenance-fg",
    Icon: Wrench,
  },
  RETIRED: {
    label: "已退役",
    bgVar: "--status-retired",
    fgVar: "--status-retired-fg",
    Icon: Moon,
  },
  DISPOSED: {
    label: "已处置",
    bgVar: "--status-disposed",
    fgVar: "--status-disposed-fg",
    Icon: Archive,
  },
};
