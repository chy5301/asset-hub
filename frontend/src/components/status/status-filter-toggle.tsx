import type { LucideIcon } from "lucide-react";

import { Toggle } from "@/components/ui/toggle";
import { cn } from "@/lib/utils";

type StatusKey = "retired" | "disposed";

const STATUS_TOKEN: Record<StatusKey, string> = {
  retired:
    "data-[state=on]:bg-status-retired/15 data-[state=on]:text-status-retired-fg data-[state=on]:border-status-retired/60",
  disposed:
    "data-[state=on]:bg-status-disposed/15 data-[state=on]:text-status-disposed-fg data-[state=on]:border-status-disposed/60",
};

interface StatusFilterToggleProps {
  pressed: boolean;
  onPressedChange: (pressed: boolean) => void;
  icon: LucideIcon;
  label: string;
  status: StatusKey;
}

/** 列表 / 看板共享的状态过滤 toggle：pill + 语义图标 + status token 染色。 */
export function StatusFilterToggle({
  pressed,
  onPressedChange,
  icon: Icon,
  label,
  status,
}: StatusFilterToggleProps) {
  return (
    <Toggle
      size="sm"
      pressed={pressed}
      onPressedChange={onPressedChange}
      className={cn(
        "rounded-full h-7 px-3 text-xs gap-1.5 transition-colors duration-200 border border-border/40",
        STATUS_TOKEN[status],
      )}
      aria-label={label}
    >
      <Icon className="size-3.5" aria-hidden />
      {label}
    </Toggle>
  );
}
