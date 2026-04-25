// frontend/src/features/assets/detail/custom-fields.tsx
import {
  formatCustomFieldValue,
  type CustomFieldDef,
} from "./custom-field-formatter";
import type { components } from "@/api/generated/schema";

type AssetRead = components["schemas"]["AssetRead"];
type TypeRead = components["schemas"]["TypeRead"];

interface CustomFieldsProps {
  asset: AssetRead;
  assetType: TypeRead | undefined;
}

export function CustomFields({ asset, assetType }: CustomFieldsProps) {
  // 类型未知（join 失败）或 schema 为空 → 整块不渲染
  const defs = (assetType?.custom_fields ?? []) as CustomFieldDef[];
  const knownKeys = new Set(defs.map((f) => f.key));
  const unknownEntries = Object.entries(asset.custom_data ?? {}).filter(
    ([k]) => !knownKeys.has(k),
  );

  if (defs.length === 0 && unknownEntries.length === 0) return null;

  return (
    <section>
      <h2 className="mb-3 text-lg font-medium">类型字段</h2>
      <dl className="divide-y divide-border/50">
        {defs.map((def) => {
          const data = asset.custom_data as Record<string, unknown> | null;
          const hasValue = data != null && def.key in data;
          return (
            <Row
              key={def.key}
              label={def.label}
              value={
                hasValue ? (
                  formatCustomFieldValue(def, data[def.key])
                ) : (
                  <span className="text-muted-foreground">—</span>
                )
              }
            />
          );
        })}
        {unknownEntries.map(([key, value]) => (
          <Row
            key={key}
            label={
              <span className="italic">
                {key}{" "}
                <small className="text-muted-foreground">（未知字段）</small>
              </span>
            }
            value={String(value)}
          />
        ))}
      </dl>
    </section>
  );
}

function Row({
  label,
  value,
}: {
  label: React.ReactNode;
  value: React.ReactNode;
}) {
  return (
    <div className="grid grid-cols-[10rem_1fr] gap-4 py-3 text-sm">
      <dt className="text-muted-foreground">{label}</dt>
      <dd>{value}</dd>
    </div>
  );
}
