import type { CSSProperties } from "react";
import { STATUS_META, type AssetStatus } from "@/features/assets/status-labels";

interface StatusBadgeProps {
  status: AssetStatus;
}

export function StatusBadge({ status }: StatusBadgeProps) {
  const meta = STATUS_META[status];
  const style: CSSProperties = {
    backgroundColor: `var(${meta.bgVar})`,
    color: `var(${meta.fgVar})`,
  };
  return (
    <span
      className="inline-flex items-center gap-1 rounded-sm px-2 py-0.5 text-xs font-medium transition-colors duration-150"
      style={style}
    >
      <meta.Icon className="h-3 w-3" aria-hidden />
      <span>{meta.label}</span>
    </span>
  );
}
