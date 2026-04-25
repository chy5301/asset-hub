import { Check, X } from "lucide-react";
import type { ReactNode } from "react";
import { formatDate } from "@/lib/date";

export type CustomFieldDef = {
  key: string;
  label: string;
  type: "string" | "text" | "int" | "float" | "bool" | "enum" | "date";
  required?: boolean;
  unique?: boolean;
  options?: string[];
};

const NUMBER_FORMATTER = new Intl.NumberFormat("zh-CN");

/**
 * 按 def.type 格式化 custom_data 的 value。
 *
 * 兼容层：
 * - value == null/undefined → "—"
 * - 类型不匹配（脏数据）→ String(value) + "（数据格式异常）"
 */
export function formatCustomFieldValue(
  def: CustomFieldDef,
  value: unknown,
): ReactNode {
  if (value === null || value === undefined) {
    return <span className="text-muted-foreground">—</span>;
  }
  try {
    switch (def.type) {
      case "string":
        return String(value);
      case "text":
        return <span className="whitespace-pre-wrap">{String(value)}</span>;
      case "int":
      case "float":
        if (typeof value !== "number") throw new Error("expected number");
        return NUMBER_FORMATTER.format(value);
      case "bool":
        return value ? (
          <Check
            className="inline-block h-4 w-4 text-[var(--status-active,#16a34a)]"
            aria-label="是"
          />
        ) : (
          <X
            className="inline-block h-4 w-4 text-muted-foreground"
            aria-label="否"
          />
        );
      case "date":
        if (typeof value !== "string") throw new Error("expected ISO string");
        return <time className="font-code">{formatDate(value)}</time>;
      case "enum":
        return String(value);
      default:
        return String(value);
    }
  } catch {
    return (
      <span>
        {String(value)}{" "}
        <small className="text-muted-foreground">（数据格式异常）</small>
      </span>
    );
  }
}
