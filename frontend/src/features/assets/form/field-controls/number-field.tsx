import type { Control, FieldValues } from 'react-hook-form';
import { Input } from '@/components/ui/input';
import { FieldShell } from './field-shell';
import type { FieldDef } from '../types';

export function NumberField<TFieldValues extends FieldValues>({
  def,
  control,
}: {
  def: FieldDef;
  control: Control<TFieldValues>;
}) {
  const inputMode = def.type === 'float' ? 'decimal' : 'numeric';
  return (
    <FieldShell def={def} control={control}>
      {(field) => (
        <div className="relative">
          <Input
            type="text"
            inputMode={inputMode}
            {...field}
            id={`field-${def.key}`}
            placeholder={def.placeholder}
            value={field.value ?? ''}
            className={def.unit ? 'pr-12' : undefined}
          />
          {def.unit && (
            <span className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-xs text-muted-foreground">
              {def.unit}
            </span>
          )}
        </div>
      )}
    </FieldShell>
  );
}
