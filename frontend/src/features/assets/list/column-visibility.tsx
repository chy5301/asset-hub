import { useEffect, useState } from "react";
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

export type ColumnKey =
  | "code"
  | "name"
  | "type"
  | "status"
  | "holder"
  | "location"
  | "updated_at";

export const COLUMN_LABELS: Record<ColumnKey, string> = {
  code: "代号",
  name: "名称",
  type: "类型",
  status: "状态",
  holder: "保管人",
  location: "位置",
  updated_at: "更新时间",
};

const STORAGE_KEY = "asset-hub.list.columns";
const ALL_KEYS: ColumnKey[] = [
  "code",
  "name",
  "type",
  "status",
  "holder",
  "location",
  "updated_at",
];

export function useColumnVisibility() {
  const [visible, setVisible] = useState<Record<ColumnKey, boolean>>(() => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw) {
        const parsed = JSON.parse(raw) as Partial<Record<ColumnKey, boolean>>;
        return Object.fromEntries(
          ALL_KEYS.map((k) => [k, parsed[k] !== false]),
        ) as Record<ColumnKey, boolean>;
      }
    } catch {
      // fall through to default
    }
    return Object.fromEntries(ALL_KEYS.map((k) => [k, true])) as Record<
      ColumnKey,
      boolean
    >;
  });

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(visible));
  }, [visible]);

  const toggle = (key: ColumnKey) =>
    setVisible((v) => ({ ...v, [key]: !v[key] }));

  return { visible, toggle };
}

interface ColumnVisibilityMenuProps {
  visible: Record<ColumnKey, boolean>;
  onToggle: (key: ColumnKey) => void;
}

export function ColumnVisibilityMenu({ visible, onToggle }: ColumnVisibilityMenuProps) {
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
