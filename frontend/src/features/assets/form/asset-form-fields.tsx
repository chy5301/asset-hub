import { useMemo } from 'react';
import { type Control, type FieldValues, type Path, useWatch } from 'react-hook-form';
import { SectionCaption } from '@/components/ui/section-heading';
import { GeneralFieldsForm } from './general-fields-form';
import { CustomFieldsForm } from './custom-fields-form';
import type { FieldDef } from './types';
import type { TypeRead } from '@/features/assets/types';

interface AssetFormFieldsProps<TFieldValues extends FieldValues> {
  control: Control<TFieldValues>;
  types: TypeRead[];
  mode: 'create' | 'edit';
  assetCode?: string;
  /** 编辑模式下用 prop 传 type_id（type_id 不在 form values 中） */
  forceTypeId?: string;
}

export function AssetFormFields<TFieldValues extends FieldValues>({
  control,
  types,
  mode,
  assetCode,
  forceTypeId,
}: AssetFormFieldsProps<TFieldValues>) {
  // 监听 type_id 切换；编辑模式下用 forceTypeId 绕过 useWatch。
  // EditFormValues 不含 type_id，故 name 用 Path<TFieldValues> 拓宽——edit 模式下
  // watchedTypeId 不会被消费（被 forceTypeId 短路），运行时安全。
  const watchedTypeId = useWatch({ control, name: 'type_id' as Path<TFieldValues> });
  const effectiveTypeId = mode === 'edit' ? forceTypeId : (watchedTypeId as string | undefined);

  const selectedType = useMemo(
    () => types.find((t) => t.id === effectiveTypeId),
    [types, effectiveTypeId],
  );
  const fieldDefs = (selectedType?.custom_fields ?? []) as FieldDef[];

  return (
    <div className="space-y-10">
      <section className="space-y-4">
        <SectionCaption>基础信息</SectionCaption>
        <GeneralFieldsForm
          control={control}
          types={types}
          typeReadonly={mode === 'edit'}
          assetCode={assetCode}
          forceTypeName={mode === 'edit' ? selectedType?.name : undefined}
          hideHolderLocation={mode === 'edit'}
        />
      </section>

      {selectedType && (
        <CustomFieldsForm
          control={control}
          fieldDefs={fieldDefs}
          typeName={selectedType.name}
        />
      )}
    </div>
  );
}
