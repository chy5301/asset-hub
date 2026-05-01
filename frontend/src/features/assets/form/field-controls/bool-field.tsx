import type { Control, FieldValues } from 'react-hook-form';
import { Checkbox } from '@/components/ui/checkbox';
import { FieldShell } from './field-shell';
import type { FieldDef } from '../types';

export function BoolField<TFieldValues extends FieldValues>({
  def,
  control,
}: {
  def: FieldDef;
  control: Control<TFieldValues>;
}) {
  return (
    <FieldShell def={def} control={control} layout="inline">
      {(field) => (
        <Checkbox
          checked={!!field.value}
          onCheckedChange={field.onChange}
          id={`field-${def.key}`}
        />
      )}
    </FieldShell>
  );
}
