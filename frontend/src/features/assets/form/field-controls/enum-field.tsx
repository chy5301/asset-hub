import type { Control, FieldValues } from 'react-hook-form';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Label } from '@/components/ui/label';
import { FieldShell } from './field-shell';
import { ENUM_INLINE_THRESHOLD, type FieldDef } from '../types';

export function EnumField<TFieldValues extends FieldValues>({
  def,
  control,
}: {
  def: FieldDef;
  control: Control<TFieldValues>;
}) {
  const options = def.options ?? [];
  const useRadio = def.displayAs === 'radio' || (def.displayAs !== 'select' && options.length <= ENUM_INLINE_THRESHOLD);

  return (
    <FieldShell def={def} control={control}>
      {(field) =>
        useRadio ? (
          <RadioGroup
            value={field.value ?? ''}
            onValueChange={field.onChange}
            className="flex flex-col gap-2"
            id={`field-${def.key}`}
          >
            {options.map((opt) => (
              <div key={opt} className="flex items-center gap-2">
                <RadioGroupItem value={opt} id={`${def.key}-${opt}`} />
                <Label htmlFor={`${def.key}-${opt}`} className="font-normal">{opt}</Label>
              </div>
            ))}
          </RadioGroup>
        ) : (
          <Select value={field.value ?? ''} onValueChange={field.onChange}>
            <SelectTrigger id={`field-${def.key}`}>
              <SelectValue placeholder={def.placeholder ?? '请选择'} />
            </SelectTrigger>
            <SelectContent>
              {options.map((opt) => (
                <SelectItem key={opt} value={opt}>{opt}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        )
      }
    </FieldShell>
  );
}
