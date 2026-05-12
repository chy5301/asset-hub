import { AlertTriangle, Archive, Circle, CircleDot, Moon, Wrench, type LucideIcon } from "lucide-react";

export type AssetStatus = "IDLE" | "IN_USE" | "MAINTENANCE" | "BROKEN" | "RETIRED" | "DISPOSED";

export interface StatusMeta {
  label: string;
  bgVar: string;
  fgVar: string;
  Icon: LucideIcon;
}

export const STATUS_META: Record<AssetStatus, StatusMeta> = {
  IDLE: {
    label: "闲置",
    bgVar: "--status-idle",
    fgVar: "--status-idle-fg",
    Icon: Circle,
  },
  IN_USE: {
    label: "在用",
    bgVar: "--status-in-use",
    fgVar: "--status-in-use-fg",
    Icon: CircleDot,
  },
  MAINTENANCE: {
    label: "送修",
    bgVar: "--status-maintenance",
    fgVar: "--status-maintenance-fg",
    Icon: Wrench,
  },
  BROKEN: {
    label: "故障",
    bgVar: "--status-broken",
    fgVar: "--status-broken-fg",
    Icon: AlertTriangle,
  },
  RETIRED: {
    label: "退役",
    bgVar: "--status-retired",
    fgVar: "--status-retired-fg",
    Icon: Moon,
  },
  DISPOSED: {
    label: "注销",
    bgVar: "--status-disposed",
    fgVar: "--status-disposed-fg",
    Icon: Archive,
  },
};
