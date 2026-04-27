import { z } from 'zod';
import { fieldDefsToZodSchema } from './field-def-to-zod';
import type { FieldDef } from './types';

const baseSchema = z.object({
  name: z.string().min(1, '资产名必填'),
  type_id: z.string().uuid('请选择资产类型'),
  serial_number: z.string().optional(),
  acquired_at: z
    .string()
    .regex(/^\d{4}-\d{2}-\d{2}$/, '日期格式 YYYY-MM-DD')
    .optional()
    .or(z.literal('')),
  holder: z.string().optional(),
  location: z.string().optional(),
  notes: z.string().optional(),
});

/**
 * 把通用字段 schema 与该 type 的 custom_fields schema 合并。
 * custom_data 嵌套在 'custom_data' key 下。
 */
export function buildCreateSchema(fieldDefs: FieldDef[]) {
  return baseSchema.extend({
    custom_data: fieldDefsToZodSchema(fieldDefs),
  });
}

export type CreateFormValues = z.infer<ReturnType<typeof buildCreateSchema>>;
