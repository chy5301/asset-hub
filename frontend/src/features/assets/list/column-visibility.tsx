import { Settings2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuCheckboxItem,
  DropdownMenuContent,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import type { COLUMN_KEY } from "./column-visibility-utils";
import { ALL_KEYS, COLUMN_LABELS } from "./column-visibility-utils";

interface ColumnVisibilityMenuProps {
  visible: Record<COLUMN_KEY, boolean>;
  onToggle: (key: COLUMN_KEY) => void;
}

export function ColumnVisibilityMenu({
  visible,
  onToggle,
}: ColumnVisibilityMenuProps) {
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="outline" size="sm" aria-label="列显隐">
          <Settings2 className="mr-2 h-4 w-4" />
          <span>列显隐</span>
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        <DropdownMenuLabel>显示列</DropdownMenuLabel>
        <DropdownMenuSeparator />
        {ALL_KEYS.map((key) => (
          <DropdownMenuCheckboxItem
            key={key}
            checked={visible[key]}
            onCheckedChange={() => onToggle(key)}
            onSelect={(e) => e.preventDefault()}
          >
            {COLUMN_LABELS[key]}
          </DropdownMenuCheckboxItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
