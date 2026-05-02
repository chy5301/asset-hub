import { z } from 'zod';
import { fieldDefsToZodSchema } from './field-def-to-zod';
import type { FieldDef } from './types';

const baseSchema = z.object({
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
});

/**
 * 把通用字段 schema 与该 type 的 custom_fields schema 合并。
 * mode='create' 含 type_id；mode='edit' 不含（D9：编辑不允许改 type）。
 */
export function buildAssetSchema(
  fieldDefs: FieldDef[],
  { mode }: { mode: 'create' | 'edit' },
) {
  const withCustom = baseSchema.extend({
    custom_data: fieldDefsToZodSchema(fieldDefs),
  });
  return mode === 'create'
    ? withCustom.extend({
        type_id: z.string().uuid('请选择资产类型'),
      })
    : withCustom;
}

// 类型别名手写而非 z.infer：buildAssetSchema 的条件 .extend 三元让 zod 推导
// 无法在 mode='create' 时正确把 type_id 加进 inferred type。Plan §Task 10 已记录此 trade-off。
export type CreateFormValues = {
  name: string;
  type_id: string;
  serial_number?: string;
  acquired_at?: string;
  holder?: string;
  location?: string;
  notes?: string;
  custom_data: Record<string, unknown>;
};
// EditFormValues = CreateFormValues 减去 create-only 字段（当前仅 type_id）
export type EditFormValues = Omit<CreateFormValues, 'type_id'>;
