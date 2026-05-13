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
  | "asset_code"
  | "name"
  | "model"
  | "serial_number"
  | "type"
  | "status"
  | "holder"
  | "location"
  | "updated_at"
  | "acquired_at";

export const COLUMN_LABELS: Record<ColumnKey, string> = {
  asset_code: "编号",
  name: "名称",
  model: "型号",
  serial_number: "SN",
  type: "类型",
  status: "状态",
  holder: "持有人",
  location: "位置",
  updated_at: "更新时间",
  acquired_at: "入账日期",
};

const STORAGE_KEY = "asset-hub.list.columns.v2";
const ALL_KEYS: ColumnKey[] = [
  "asset_code",
  "name",
  "model",
  "serial_number",
  "type",
  "status",
  "holder",
  "location",
  "updated_at",
  "acquired_at",
];
const DEFAULT_HIDDEN: Set<ColumnKey> = new Set(["acquired_at"]);

function loadStored(): Partial<Record<ColumnKey, boolean>> {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? (JSON.parse(raw) as Partial<Record<ColumnKey, boolean>>) : {};
  } catch {
    return {};
  }
}

export function useColumnVisibility() {
  const [visible, setVisible] = useState<Record<ColumnKey, boolean>>(() => {
    const stored = loadStored();
    return Object.fromEntries(
      ALL_KEYS.map((k) => [
        k,
        stored[k] !== undefined ? stored[k] : !DEFAULT_HIDDEN.has(k),
      ]),
    ) as Record<ColumnKey, boolean>;
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
