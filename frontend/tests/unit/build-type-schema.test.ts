import { describe, expect, it } from 'vitest';
import { buildTypeSchema } from '@/features/types/form/build-type-schema';

describe('buildTypeSchema', () => {
  describe('顶层字段', () => {
    it('create 模式 code_prefix 必填', () => {
      const schema = buildTypeSchema({ mode: 'create' });
      const r = schema.safeParse({ name: 'X', custom_fields: [] });
      expect(r.success).toBe(false);
    });

    it('edit 模式 code_prefix 不要求', () => {
      const schema = buildTypeSchema({ mode: 'edit' });
      const r = schema.safeParse({ name: 'X', custom_fields: [] });
      expect(r.success).toBe(true);
    });

    it('code_prefix 正则 ^[A-Z]{2,4}$', () => {
      const schema = buildTypeSchema({ mode: 'create' });
      expect(schema.safeParse({ name: 'X', code_prefix: 'NB', custom_fields: [] }).success).toBe(true);
      expect(schema.safeParse({ name: 'X', code_prefix: 'N', custom_fields: [] }).success).toBe(false);
      expect(schema.safeParse({ name: 'X', code_prefix: 'LAPTOP', custom_fields: [] }).success).toBe(false);
      expect(schema.safeParse({ name: 'X', code_prefix: 'nb', custom_fields: [] }).success).toBe(false);
    });

    it('name 必填', () => {
      const schema = buildTypeSchema({ mode: 'edit' });
      expect(schema.safeParse({ name: '', custom_fields: [] }).success).toBe(false);
    });
  });

  describe('fieldDefSchema 单字段', () => {
    const schema = buildTypeSchema({ mode: 'edit' });

    it('key 正则 ^[a-z][a-z0-9_]*$', () => {
      const bad = schema.safeParse({
        name: 'X',
        custom_fields: [{ key: 'CPU', type: 'string' }],
      });
      expect(bad.success).toBe(false);
    });

    it('type 限定 9 种枚举', () => {
      const bad = schema.safeParse({
        name: 'X',
        custom_fields: [{ key: 'k', type: 'unknown_type' }],
      });
      expect(bad.success).toBe(false);
    });
  });

  describe('superRefine 跨字段', () => {
    const schema = buildTypeSchema({ mode: 'edit' });

    it('数组级 key 唯一性', () => {
      const r = schema.safeParse({
        name: 'X',
        custom_fields: [
          { key: 'cpu', type: 'string' },
          { key: 'cpu', type: 'int' },
        ],
      });
      expect(r.success).toBe(false);
      if (!r.success) {
        const dupErr = r.error.issues.find((i) =>
          i.path.includes('key') && i.message.includes('已被使用'),
        );
        expect(dupErr).toBeDefined();
      }
    });

    it('min ≤ max（int/float）', () => {
      const r = schema.safeParse({
        name: 'X',
        custom_fields: [{ key: 'k', type: 'int', min: 100, max: 10 }],
      });
      expect(r.success).toBe(false);
    });

    it('enum 必须有 options 且非空', () => {
      const r = schema.safeParse({
        name: 'X',
        custom_fields: [{ key: 'k', type: 'enum', options: [] }],
      });
      expect(r.success).toBe(false);
    });

    it('options 唯一性', () => {
      const r = schema.safeParse({
        name: 'X',
        custom_fields: [
          { key: 'k', type: 'enum', options: ['A', 'A', 'B'] },
        ],
      });
      expect(r.success).toBe(false);
    });
  });
});
