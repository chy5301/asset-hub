import { z } from 'zod';
import type { FieldDef } from './types';

/**
 * 把 FieldDef[] 编译成一个 ZodObject，作为 RHF 表单的 schema。
 *
 * 规则（spec §5.6 / D7）：
 * - string/text: z.string()，required → .min(1)
 * - int: z.coerce.number().int()，可选 min/max
 * - float: z.coerce.number()，可选 min/max
 * - bool: z.boolean()，默认 false
 * - date: z.string().regex(YYYY-MM-DD)
 * - enum: z.enum(options)
 * - multi-enum: z.array(z.enum(options))
 * - url: z.string().url()
 *
 * unit 字段不参与校验（仅显示）。
 */
export function fieldDefsToZodSchema(defs: FieldDef[]): z.ZodObject<z.ZodRawShape> {
  const shape: z.ZodRawShape = {};
  for (const def of defs) {
    shape[def.key] = buildFieldSchema(def);
  }
  return z.object(shape);
}

function buildFieldSchema(def: FieldDef): z.ZodTypeAny {
  switch (def.type) {
    case 'string':
    case 'text': {
      if (def.required) {
        return z.string().min(1, `${def.label ?? def.key} 必填`);
      }
      return z.string().optional().or(z.literal(''));
    }
    case 'int': {
      let s = z.coerce.number().int(`${def.label ?? def.key} 必须是整数`);
      if (def.min != null) s = s.min(def.min);
      if (def.max != null) s = s.max(def.max);
      return def.required ? s : s.optional();
    }
    case 'float': {
      let s = z.coerce.number();
      if (def.min != null) s = s.min(def.min);
      if (def.max != null) s = s.max(def.max);
      return def.required ? s : s.optional();
    }
    case 'bool': {
      return z.boolean().optional().default(false);
    }
    case 'date': {
      const s = z.string().regex(
        /^\d{4}-\d{2}-\d{2}$/,
        `${def.label ?? def.key} 必须是 YYYY-MM-DD 格式`,
      );
      return def.required ? s : s.optional().or(z.literal(''));
    }
    case 'enum': {
      const opts = def.options ?? [];
      if (opts.length === 0) {
        return def.required ? z.string().min(1) : z.string().optional();
      }
      const e = z.enum(opts as [string, ...string[]]);
      return def.required ? e : e.optional();
    }
    case 'multi-enum': {
      const opts = def.options ?? [];
      if (opts.length === 0) {
        return z.array(z.string()).optional().default([]);
      }
      const arr = z.array(z.enum(opts as [string, ...string[]]));
      return def.required ? arr.min(1) : arr.optional().default([]);
    }
    case 'url': {
      const s = z.string().url(`${def.label ?? def.key} 必须是合法 URL`);
      return def.required ? s : s.optional().or(z.literal(''));
    }
  }
}
