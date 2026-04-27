import { describe, expect, it } from 'vitest';
import { fieldDefsToZodSchema } from '@/features/assets/form/field-def-to-zod';
import type { FieldDef } from '@/features/assets/form/types';

describe('fieldDefsToZodSchema', () => {
  it('string required: rejects empty, accepts non-empty', () => {
    const schema = fieldDefsToZodSchema([{ key: 'cpu', type: 'string', required: true }]);
    expect(schema.safeParse({ cpu: '' }).success).toBe(false);
    expect(schema.safeParse({ cpu: 'i7' }).success).toBe(true);
  });

  it('string optional: accepts empty/undefined', () => {
    const schema = fieldDefsToZodSchema([{ key: 'cpu', type: 'string' }]);
    expect(schema.safeParse({}).success).toBe(true);
    expect(schema.safeParse({ cpu: '' }).success).toBe(true);
  });

  it('int: coerces string to number, rejects float', () => {
    const schema = fieldDefsToZodSchema([{ key: 'ram', type: 'int', required: true }]);
    const r = schema.safeParse({ ram: '32' });
    expect(r.success).toBe(true);
    if (r.success) expect(r.data.ram).toBe(32);

    expect(schema.safeParse({ ram: '32.5' }).success).toBe(false);
    expect(schema.safeParse({ ram: 'not-a-number' }).success).toBe(false);
  });

  it('int with min/max', () => {
    const schema = fieldDefsToZodSchema([
      { key: 'ram', type: 'int', required: true, min: 1, max: 128 },
    ]);
    expect(schema.safeParse({ ram: '0' }).success).toBe(false);
    expect(schema.safeParse({ ram: '256' }).success).toBe(false);
    expect(schema.safeParse({ ram: '32' }).success).toBe(true);
  });

  it('float: accepts decimal', () => {
    const schema = fieldDefsToZodSchema([{ key: 'weight', type: 'float', required: true }]);
    const r = schema.safeParse({ weight: '1.13' });
    expect(r.success).toBe(true);
    if (r.success) expect(r.data.weight).toBeCloseTo(1.13);
  });

  it('bool: accepts true/false', () => {
    const schema = fieldDefsToZodSchema([{ key: 'is_new', type: 'bool' }]);
    expect(schema.safeParse({ is_new: true }).success).toBe(true);
    expect(schema.safeParse({ is_new: false }).success).toBe(true);
    expect(schema.safeParse({}).success).toBe(true); // optional
  });

  it('date: ISO format', () => {
    const schema = fieldDefsToZodSchema([{ key: 'warranty', type: 'date', required: true }]);
    expect(schema.safeParse({ warranty: '2026-04-26' }).success).toBe(true);
    expect(schema.safeParse({ warranty: '2026/04/26' }).success).toBe(false);
    expect(schema.safeParse({ warranty: '' }).success).toBe(false);
  });

  it('enum: only accepts options', () => {
    const schema = fieldDefsToZodSchema([
      { key: 'color', type: 'enum', required: true, options: ['银色', '黑色', '深空灰'] },
    ]);
    expect(schema.safeParse({ color: '银色' }).success).toBe(true);
    expect(schema.safeParse({ color: '红色' }).success).toBe(false);
  });

  it('multi-enum: array of options', () => {
    const schema = fieldDefsToZodSchema([
      { key: 'ports', type: 'multi-enum', options: ['Type-C', 'HDMI', 'USB-A'] },
    ]);
    expect(schema.safeParse({ ports: ['Type-C', 'HDMI'] }).success).toBe(true);
    expect(schema.safeParse({ ports: ['Type-C', 'XYZ'] }).success).toBe(false);
    expect(schema.safeParse({ ports: [] }).success).toBe(true); // optional
  });

  it('url: rejects non-url', () => {
    const schema = fieldDefsToZodSchema([{ key: 'site', type: 'url', required: true }]);
    expect(schema.safeParse({ site: 'https://example.com' }).success).toBe(true);
    expect(schema.safeParse({ site: 'not-a-url' }).success).toBe(false);
  });

  it('combined: multi-field schema', () => {
    const schema = fieldDefsToZodSchema([
      { key: 'cpu', type: 'string', required: true },
      { key: 'ram', type: 'int', required: true },
      { key: 'has_lid', type: 'bool' },
    ] satisfies FieldDef[]);
    expect(schema.safeParse({ cpu: 'i7', ram: '32' }).success).toBe(true);
    expect(schema.safeParse({ cpu: 'i7' }).success).toBe(false); // ram required
  });
});
