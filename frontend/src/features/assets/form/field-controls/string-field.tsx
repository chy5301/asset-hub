import type { Control, FieldValues } from 'react-hook-form';
import { Input } from '@/components/ui/input';
import { FieldShell } from './field-shell';
import type { FieldDef } from '../types';

export function StringField<TFieldValues extends FieldValues>({
  def,
  control,
}: {
  def: FieldDef;
  control: Control<TFieldValues>;
}) {
  return (
    <FieldShell def={def} control={control}>
      {(field) => (
        <Input
          {...field}
          id={`field-${def.key}`}
          placeholder={def.placeholder}
          value={field.value ?? ''}
        />
      )}
    </FieldShell>
  );
}
