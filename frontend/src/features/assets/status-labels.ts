import { Circle, CircleDot, MinusCircle, Wrench, type LucideIcon } from "lucide-react";

export type AssetStatus = "IN_USE" | "IDLE" | "MAINTENANCE" | "RETIRED";

export interface StatusMeta {
  label: string;
  bgVar: string;
  fgVar: string;
  Icon: LucideIcon;
}

export const STATUS_META: Record<AssetStatus, StatusMeta> = {
  IN_USE: {
    label: "在用",
    bgVar: "--status-in-use",
    fgVar: "--status-in-use-fg",
    Icon: CircleDot,
  },
  IDLE: {
    label: "闲置",
    bgVar: "--status-idle",
    fgVar: "--status-idle-fg",
    Icon: Circle,
  },
  MAINTENANCE: {
    label: "维护",
    bgVar: "--status-maintenance",
    fgVar: "--status-maintenance-fg",
    Icon: Wrench,
  },
  RETIRED: {
    label: "报废",
    bgVar: "--status-retired",
    fgVar: "--status-retired-fg",
    Icon: MinusCircle,
  },
};
