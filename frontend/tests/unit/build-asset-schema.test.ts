import { describe, expect, it } from 'vitest';
import { buildAssetSchema } from '@/features/assets/form/build-asset-schema';
import type { FieldDef } from '@/features/assets/form/types';

describe('buildAssetSchema', () => {
  it("mode='create' 包含 type_id", () => {
    const schema = buildAssetSchema([], { mode: 'create' });
    const result = schema.safeParse({
      name: 'x',
      // 缺 type_id
      custom_data: {},
    });
    expect(result.success).toBe(false);
    if (!result.success) {
      expect(result.error.issues.some((i) => i.path[0] === 'type_id')).toBe(true);
    }
  });

  it("mode='edit' 不要求 type_id", () => {
    const schema = buildAssetSchema([], { mode: 'edit' });
    const result = schema.safeParse({
      name: 'x',
      custom_data: {},
    });
    expect(result.success).toBe(true);
  });

  it('注入 fieldDefs 后 custom_data 子 schema 生效', () => {
    const fieldDefs: FieldDef[] = [
      { key: 'cpu', type: 'string', required: true },
    ];
    const schema = buildAssetSchema(fieldDefs, { mode: 'edit' });
    const result = schema.safeParse({
      name: 'x',
      custom_data: { cpu: '' }, // required string min(1)
    });
    expect(result.success).toBe(false);
  });

  it('create + 合法值通过', () => {
    const schema = buildAssetSchema([], { mode: 'create' });
    const result = schema.safeParse({
      name: 'x',
      type_id: '00000000-0000-0000-0000-000000000000',
      custom_data: {},
    });
    expect(result.success).toBe(true);
  });
});
