import { useMemo } from 'react';
import { type Control, useWatch } from 'react-hook-form';
import { GeneralFieldsForm } from './general-fields-form';
import { CustomFieldsForm } from './custom-fields-form';
import type { FieldDef } from './types';
import type { components } from '@/api/generated/schema';

type AssetTypeRead = components['schemas']['TypeRead'];

interface AssetFormFieldsProps {
  control: Control;
  types: AssetTypeRead[];
  mode: 'create' | 'edit';
  assetCode?: string;
  /** 编辑模式下用 prop 传 type_id（type_id 不在 form values 中） */
  forceTypeId?: string;
}

export function AssetFormFields({ control, types, mode, assetCode, forceTypeId }: AssetFormFieldsProps) {
  // 监听 type_id 切换；编辑模式下用 forceTypeId 绕过 useWatch
  const watchedTypeId = useWatch({ control, name: 'type_id' });
  const effectiveTypeId = mode === 'edit' ? forceTypeId : watchedTypeId;

  const selectedType = useMemo(
    () => types.find((t) => t.id === effectiveTypeId),
    [types, effectiveTypeId],
  );
  const fieldDefs = (selectedType?.custom_fields ?? []) as FieldDef[];

  return (
    <div className="space-y-10">
      <section className="space-y-4">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-foreground border-b pb-1.5">
          基础信息
        </h2>
        <GeneralFieldsForm
          control={control}
          types={types}
          typeReadonly={mode === 'edit'}
          assetCode={assetCode}
          forceTypeName={mode === 'edit' ? selectedType?.name : undefined}
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
