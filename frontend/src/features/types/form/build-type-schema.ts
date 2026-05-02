import { z } from 'zod';

const fieldTypeEnum = z.enum([
  'string', 'text', 'url', 'int', 'float',
  'bool', 'date', 'enum', 'multi-enum',
]);

export const fieldDefSchema = z
  .object({
    key: z
      .string()
      .min(1, 'key 必填')
      .regex(/^[a-z][a-z0-9_]*$/, 'key 需 snake_case（小写字母开头）'),
    label: z.string().optional(),
    type: fieldTypeEnum,
    required: z.boolean().default(false),
    placeholder: z.string().optional(),
    help: z.string().optional(),
    default: z
      .union([z.string(), z.number(), z.boolean(), z.null()])
      .optional(),
    unit: z.string().optional(),
    min: z.number().optional(),
    max: z.number().optional(),
    options: z.array(z.string()).optional(),
    displayAs: z.enum(['radio', 'select']).optional(),
  })
  .superRefine((def, ctx) => {
    if (
      (def.type === 'int' || def.type === 'float') &&
      def.min != null &&
      def.max != null &&
      def.min > def.max
    ) {
      ctx.addIssue({
        path: ['max'],
        code: 'custom',
        message: `max 不能小于 min（${def.min}）`,
      });
    }
    if (
      (def.type === 'enum' || def.type === 'multi-enum') &&
      (!def.options || def.options.length === 0)
    ) {
      ctx.addIssue({
        path: ['options'],
        code: 'custom',
        message: '需要至少 1 个选项',
      });
    }
    if (def.options) {
      const seen = new Set<string>();
      def.options.forEach((opt, i) => {
        if (seen.has(opt)) {
          ctx.addIssue({
            path: ['options', i],
            code: 'custom',
            message: `选项 '${opt}' 已存在`,
          });
        }
        seen.add(opt);
      });
    }
  });

const customFieldsArraySchema = z
  .array(fieldDefSchema)
  .superRefine((fields, ctx) => {
    const seen = new Map<string, number>();
    fields.forEach((f, i) => {
      if (seen.has(f.key)) {
        ctx.addIssue({
          path: [i, 'key'],
          code: 'custom',
          message: `key '${f.key}' 已被使用`,
        });
      }
      seen.set(f.key, i);
    });
  });

export function buildTypeSchema({ mode }: { mode: 'create' | 'edit' }) {
  const base = z.object({
    name: z.string().min(1, '类型名必填'),
    description: z.string().optional(),
    custom_fields: customFieldsArraySchema,
  });
  return mode === 'create'
    ? base.extend({
        code_prefix: z
          .string()
          .regex(/^[A-Z]{2,4}$/, 'code_prefix 需 2-4 个大写字母'),
      })
    : base;
}

export type FieldDefFormValue = z.infer<typeof fieldDefSchema>;

// 类型别名手写而非 z.infer：buildTypeSchema 的条件 .extend 三元让 zod 推导
// 在 'create' 分支丢失 code_prefix（与 build-asset-schema.ts 的 §J/§L trade-off 同源）。
// 跨字段校验仍由 superRefine 兜住，类型层只负责让 RHF/TypeForm 看到正确字段集合。
export type EditTypeFormValues = {
  name: string;
  description?: string;
  custom_fields: FieldDefFormValue[];
};
// CreateTypeFormValues = EditTypeFormValues 加上 create-only 字段（code_prefix）
export type CreateTypeFormValues = EditTypeFormValues & {
  code_prefix: string;
};
