import {
  formatCustomFieldValue,
  type CustomFieldDef,
} from "./custom-field-formatter";
import { DefinitionRow } from "./definition-row";
import type { components } from "@/api/generated/schema";

type AssetRead = components["schemas"]["AssetRead"];
type TypeRead = components["schemas"]["TypeRead"];

interface CustomFieldsProps {
  asset: AssetRead;
  assetType: TypeRead | undefined;
}

export function CustomFields({ asset, assetType }: CustomFieldsProps) {
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
            <DefinitionRow key={def.key} label={def.label ?? def.key}>
              {hasValue ? (
                formatCustomFieldValue(def, data[def.key])
              ) : (
                <span className="text-muted-foreground">—</span>
              )}
            </DefinitionRow>
          );
        })}
        {unknownEntries.map(([key, value]) => (
          <DefinitionRow
            key={key}
            label={
              <span className="italic">
                {key}{" "}
                <small className="text-muted-foreground">（未知字段）</small>
              </span>
            }
          >
            {String(value)}
          </DefinitionRow>
        ))}
      </dl>
    </section>
  );
}
