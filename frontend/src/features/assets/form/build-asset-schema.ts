import { z } from 'zod';
import { fieldDefsToZodSchema } from './field-def-to-zod';
import type { FieldDef } from './types';

const baseShape = {
  name: z.string().min(1, '资产名必填'),
  serial_number: z.string().optional(),
  acquired_at: z
    .string()
    .regex(/^\d{4}-\d{2}-\d{2}$/, '日期格式 YYYY-MM-DD')
    .optional()
    .or(z.literal('')),
  holder: z.string().optional(),
  location: z.string().optional(),
  notes: z.string().optional(),
};

/**
 * 单 builder + 显式 mode 分支（修订前是双函数 + 条件 .extend，导致 zod inference 丢 type_id 必须 cast Resolver）。
 *
 * 关键：用 z.object({...}) 静态展开、不带条件 .extend——zod 推导可通过类型层面对 type_id 必填/可选准确反射。
 */
export function buildAssetSchema(
  fieldDefs: FieldDef[],
  { mode }: { mode: 'create' | 'edit' },
) {
  const customFieldsSchema = fieldDefsToZodSchema(fieldDefs);

  if (mode === 'create') {
    return z.object({
      ...baseShape,
      type_id: z.string().uuid('请选择资产类型'),
      custom_data: customFieldsSchema,
    });
  }

  return z.object({
    ...baseShape,
    custom_data: customFieldsSchema,
  });
}

export type CreateFormValues = z.infer<ReturnType<typeof buildAssetSchema>> & { type_id: string };
export type EditFormValues = z.infer<ReturnType<typeof buildAssetSchema>>;
