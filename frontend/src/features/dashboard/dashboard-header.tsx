import { HelpCircle } from "lucide-react";

import { cn } from "@/lib/utils";

import type { DashboardSearch } from "./search-schema";

interface DashboardHeaderProps {
  includeRetired: boolean;
  includeDisposed: boolean;
  onToggle: (next: DashboardSearch) => void;
}

/**
 * 看板顶栏: h1 + 副标 + inline pill toggle (spec §B.fd3 基线对齐).
 *
 * 形态约束: 拒绝 SaaS 模板的"右上角 standalone toggle button";
 * inline pill 形态 + dot 前缀指示 on/off + status token 弱化版 active 态.
 */
export function DashboardHeader({ includeRetired, includeDisposed, onToggle }: DashboardHeaderProps) {
  return (
    <div className="mb-8 flex items-baseline justify-between">
      <div className="flex flex-col gap-1">
        <h1 className="text-3xl font-medium tracking-tight">看板</h1>
        <p className="text-sm text-muted-foreground">实时盘点 + 闲置督促</p>
      </div>

      <div className="flex items-center gap-3">
        <TogglePill
          label="已退役"
          tokenClass="data-[state=on]:bg-status-retired/15 data-[state=on]:text-status-retired-fg"
          state={includeRetired ? "on" : "off"}
          onClick={() =>
            onToggle({
              include_retired: !includeRetired,
              include_disposed: includeDisposed,
            })
          }
        />
        <TogglePill
          label="已处置"
          tokenClass="data-[state=on]:bg-status-disposed/15 data-[state=on]:text-status-disposed-fg"
          state={includeDisposed ? "on" : "off"}
          onClick={() =>
            onToggle({
              include_retired: includeRetired,
              include_disposed: !includeDisposed,
            })
          }
        />
        <HelpCircle className="size-3.5 text-muted-foreground/60" aria-label="提示">
          <title>默认排除已退役/已处置(与列表一致)</title>
        </HelpCircle>
      </div>
    </div>
  );
}

interface TogglePillProps {
  label: string;
  tokenClass: string;
  state: "on" | "off";
  onClick: () => void;
}

function TogglePill({ label, tokenClass, state, onClick }: TogglePillProps) {
  return (
    <button
      type="button"
      data-state={state}
      onClick={onClick}
      aria-label={label}
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium",
        "border-border/60 text-muted-foreground transition-colors",
        "hover:bg-muted",
        tokenClass,
      )}
    >
      <span
        className={cn(
          "size-1.5 rounded-full transition-colors",
          state === "on" ? "bg-current" : "bg-muted-foreground/40",
        )}
      />
      {label}
    </button>
  );
}
