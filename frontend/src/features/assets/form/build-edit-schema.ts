import { z } from 'zod';
import { fieldDefsToZodSchema } from './field-def-to-zod';
import type { FieldDef } from './types';

const baseEditSchema = z.object({
  name: z.string().min(1, '资产名必填'),
  // type_id 不在 EditSchema 中——D9 不允许改
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
 * 编辑表单 schema：通用字段 + 该 type 的 custom_fields。
 * 编辑模式不允许改 type，因此 type_id 不在 schema 内。
 */
export function buildEditSchema(fieldDefs: FieldDef[]) {
  return baseEditSchema.extend({
    custom_data: fieldDefsToZodSchema(fieldDefs),
  });
}

export type EditFormValues = z.infer<ReturnType<typeof buildEditSchema>>;
