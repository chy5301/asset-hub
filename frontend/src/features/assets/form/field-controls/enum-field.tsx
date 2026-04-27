import { type Control } from 'react-hook-form';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { FormField, FormItem, FormLabel, FormControl, FormDescription, FormMessage } from '@/components/ui/form';
import { Label } from '@/components/ui/label';
import { ENUM_INLINE_THRESHOLD, type FieldDef } from '../types';

export function EnumField({ def, control }: { def: FieldDef; control: Control }) {
  const options = def.options ?? [];
  const useRadio = def.displayAs === 'radio' || (def.displayAs !== 'select' && options.length <= ENUM_INLINE_THRESHOLD);

  return (
    <FormField
      control={control}
      name={`custom_data.${def.key}`}
      render={({ field }) => (
        <FormItem>
          <FormLabel>
            {def.label ?? def.key}
            {def.required && <span className="ml-1 text-destructive">*</span>}
          </FormLabel>
          <FormControl>
            {useRadio ? (
              <RadioGroup value={field.value ?? ''} onValueChange={field.onChange} className="flex flex-col gap-2">
                {options.map((opt) => (
                  <div key={opt} className="flex items-center gap-2">
                    <RadioGroupItem value={opt} id={`${def.key}-${opt}`} />
                    <Label htmlFor={`${def.key}-${opt}`} className="font-normal">{opt}</Label>
                  </div>
                ))}
              </RadioGroup>
            ) : (
              <Select value={field.value ?? ''} onValueChange={field.onChange}>
                <SelectTrigger>
                  <SelectValue placeholder={def.placeholder ?? '请选择'} />
                </SelectTrigger>
                <SelectContent>
                  {options.map((opt) => (
                    <SelectItem key={opt} value={opt}>{opt}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            )}
          </FormControl>
          {def.help && <FormDescription>{def.help}</FormDescription>}
          <FormMessage />
        </FormItem>
      )}
    />
  );
}
