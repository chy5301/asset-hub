import type { Control, UseFormSetValue, FieldErrors } from 'react-hook-form';
import { Controller, useWatch } from 'react-hook-form';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Checkbox } from '@/components/ui/checkbox';
import { Label } from '@/components/ui/label';
import { FieldTypeSelector } from './field-type-selector';
import { FieldOptionsEditor } from './field-options-editor';
import type { CreateTypeFormValues } from '../build-type-schema';

interface Props {
  control: Control<CreateTypeFormValues>;
  setValue: UseFormSetValue<CreateTypeFormValues>;
  index: number;
  errors?: FieldErrors<CreateTypeFormValues>;
}

export function FieldAttributeForm({ control, setValue, index, errors }: Props) {
  const path = `custom_fields.${index}` as const;
  const fieldType = useWatch({ control, name: `${path}.type` });
  const fieldErr = errors?.custom_fields?.[index];

  function onTypeChange(newType: string) {
    setValue(`${path}.type` as never, newType as never);
    // 切 type 时清空 type-specific 属性
    setValue(`${path}.unit` as never, undefined as never);
    setValue(`${path}.min` as never, undefined as never);
    setValue(`${path}.max` as never, undefined as never);
    setValue(`${path}.options` as never, undefined as never);
    setValue(`${path}.displayAs` as never, undefined as never);
  }

  return (
    <div className="space-y-4 p-4">
      <div className="grid grid-cols-2 gap-4">
        <div>
          <Label htmlFor={`field-${index}-key`}>key *</Label>
          <Controller
            control={control}
            name={`${path}.key` as never}
            render={({ field }) => <Input id={`field-${index}-key`} {...field} placeholder="snake_case" />}
          />
          {fieldErr?.key && <p className="text-sm text-destructive mt-1">{fieldErr.key.message as string}</p>}
        </div>
        <div>
          <Label htmlFor={`field-${index}-type`}>type *</Label>
          <Controller
            control={control}
            name={`${path}.type` as never}
            render={({ field }) => (
              <FieldTypeSelector id={`field-${index}-type`} value={field.value} onChange={onTypeChange} />
            )}
          />
        </div>
        <div>
          <Label htmlFor={`field-${index}-label`}>label</Label>
          <Controller
            control={control}
            name={`${path}.label` as never}
            render={({ field }) => <Input id={`field-${index}-label`} {...field} value={field.value ?? ''} placeholder="显示名" />}
          />
        </div>
        <div className="flex items-center gap-2 mt-6">
          <Controller
            control={control}
            name={`${path}.required` as never}
            render={({ field }) => (
              <Checkbox
                checked={!!field.value}
                onCheckedChange={field.onChange}
                id={`required-${index}`}
              />
            )}
          />
          <Label htmlFor={`required-${index}`}>必填</Label>
        </div>
      </div>

      <div>
        <Label htmlFor={`field-${index}-placeholder`}>placeholder</Label>
        <Controller
          control={control}
          name={`${path}.placeholder` as never}
          render={({ field }) => <Input id={`field-${index}-placeholder`} {...field} value={field.value ?? ''} />}
        />
      </div>

      <div>
        <Label htmlFor={`field-${index}-help`}>help</Label>
        <Controller
          control={control}
          name={`${path}.help` as never}
          render={({ field }) => <Textarea id={`field-${index}-help`} {...field} value={field.value ?? ''} rows={2} />}
        />
      </div>

      {(fieldType === 'int' || fieldType === 'float') && (
        <div className="grid grid-cols-3 gap-4">
          <div>
            <Label htmlFor={`field-${index}-unit`}>unit</Label>
            <Controller
              control={control}
              name={`${path}.unit` as never}
              render={({ field }) => <Input id={`field-${index}-unit`} {...field} value={field.value ?? ''} placeholder="GB / mm 等" />}
            />
          </div>
          <div>
            <Label htmlFor={`field-${index}-min`}>min</Label>
            <Controller
              control={control}
              name={`${path}.min` as never}
              render={({ field }) => (
                <Input
                  id={`field-${index}-min`}
                  type="number"
                  value={field.value ?? ''}
                  onChange={(e) =>
                    field.onChange(e.target.value === '' ? undefined : Number(e.target.value))
                  }
                />
              )}
            />
          </div>
          <div>
            <Label htmlFor={`field-${index}-max`}>max</Label>
            <Controller
              control={control}
              name={`${path}.max` as never}
              render={({ field }) => (
                <Input
                  id={`field-${index}-max`}
                  type="number"
                  value={field.value ?? ''}
                  onChange={(e) =>
                    field.onChange(e.target.value === '' ? undefined : Number(e.target.value))
                  }
                />
              )}
            />
            {fieldErr?.max && <p className="text-sm text-destructive mt-1">{fieldErr.max.message as string}</p>}
          </div>
        </div>
      )}

      {(fieldType === 'enum' || fieldType === 'multi-enum') && (
        <div>
          <Label htmlFor={`field-${index}-options`}>options *</Label>
          <Controller
            control={control}
            name={`${path}.options` as never}
            render={({ field }) => {
              const errorIndices = Array.isArray(fieldErr?.options)
                ? (fieldErr.options as { message?: string }[])
                    .map((e, i) => (e ? i : -1))
                    .filter((i) => i >= 0)
                : [];
              return (
                <FieldOptionsEditor
                  id={`field-${index}-options`}
                  value={field.value ?? []}
                  onChange={field.onChange}
                  errorPaths={errorIndices}
                />
              );
            }}
          />
          {fieldErr?.options && typeof (fieldErr.options as { message?: string }).message === 'string' && (
            <p className="text-sm text-destructive mt-1">
              {(fieldErr.options as { message: string }).message}
            </p>
          )}
        </div>
      )}
    </div>
  );
}
