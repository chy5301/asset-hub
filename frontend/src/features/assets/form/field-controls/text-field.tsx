import type { Control, FieldValues } from 'react-hook-form';
import { Textarea } from '@/components/ui/textarea';
import { FieldShell } from './field-shell';
import type { FieldDef } from '../types';

export function TextField<TFieldValues extends FieldValues>({
  def,
  control,
}: {
  def: FieldDef;
  control: Control<TFieldValues>;
}) {
  return (
    <FieldShell def={def} control={control}>
      {(field) => (
        <Textarea
          {...field}
          id={`field-${def.key}`}
          placeholder={def.placeholder}
          value={field.value ?? ''}
          rows={3}
        />
      )}
    </FieldShell>
  );
}
