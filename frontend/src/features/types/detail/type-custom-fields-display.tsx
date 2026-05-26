import type { TypeRead } from "@/features/assets/types";

type Field = TypeRead["custom_fields"][number];

/** 类型只读视图里的 custom_fields schema 展示（只读，非编辑）。 */
export function TypeCustomFieldsDisplay({ fields }: { fields: Field[] }) {
  if (fields.length === 0) {
    return <p className="text-sm text-muted-foreground">无自定义字段</p>;
  }
  return (
    <ul className="divide-y divide-border/50">
      {fields.map((f) => (
        <li
          key={f.key}
          className="grid grid-cols-[1fr_auto] items-baseline gap-4 py-3 text-sm"
        >
          <div className="space-y-0.5">
            <div className="flex items-center gap-2">
              <span className="font-medium">{f.label || f.key}</span>
              <span className="font-code text-xs text-muted-foreground">
                {f.key}
              </span>
              {f.required && (
                <span className="text-xs text-muted-foreground">必填</span>
              )}
            </div>
            {f.options && f.options.length > 0 && (
              <p className="text-xs text-muted-foreground">
                选项：{f.options.join("、")}
              </p>
            )}
          </div>
          <span className="font-code text-xs text-muted-foreground">
            {f.type}
          </span>
        </li>
      ))}
    </ul>
  );
}
