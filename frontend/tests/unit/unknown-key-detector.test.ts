import { describe, expect, it } from 'vitest';
import { detectUnknownKeys } from '@/lib/unknown-key-detector';
import type { FieldDef } from '@/features/assets/form/types';

describe('detectUnknownKeys', () => {
  it('orphan keys: custom_data 有 fieldDefs 没有的 key', () => {
    const fieldDefs: FieldDef[] = [{ key: 'cpu', type: 'string' }];
    const customData = { cpu: 'i7', ram_gb: 16 };
    const r = detectUnknownKeys(customData, fieldDefs);
    expect(r.orphanKeys).toEqual(['ram_gb']);
    expect(r.violatedRequired).toEqual([]);
    expect(r.hasIssues).toBe(true);
  });

  it('violatedRequired: required field 在 custom_data 中为 null/undefined', () => {
    const fieldDefs: FieldDef[] = [
      { key: 'brand', type: 'string', required: true },
      { key: 'cpu', type: 'string', required: false },
    ];
    const r = detectUnknownKeys({ cpu: 'i7' }, fieldDefs);
    expect(r.violatedRequired).toEqual([{ key: 'brand' }]);
  });

  it('两者皆空时 hasIssues = false', () => {
    const fieldDefs: FieldDef[] = [{ key: 'cpu', type: 'string' }];
    const r = detectUnknownKeys({ cpu: 'i7' }, fieldDefs);
    expect(r.hasIssues).toBe(false);
    expect(r.orphanKeys).toEqual([]);
    expect(r.violatedRequired).toEqual([]);
  });
});
