import type { FieldDef } from '@/features/assets/form/types';

export interface UnknownKeyReport {
  orphanKeys: string[];
  violatedRequired: { key: string }[];
  hasIssues: boolean;
}

export function detectUnknownKeys(
  customData: Record<string, unknown>,
  fieldDefs: FieldDef[],
): UnknownKeyReport {
  const declared = new Set(fieldDefs.map((f) => f.key));
  const orphanKeys = Object.keys(customData).filter((k) => !declared.has(k));
  const violatedRequired = fieldDefs
    .filter((f) => f.required && customData[f.key] == null)
    .map((f) => ({ key: f.key }));
  return {
    orphanKeys,
    violatedRequired,
    hasIssues: orphanKeys.length > 0 || violatedRequired.length > 0,
  };
}
