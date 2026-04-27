import { type Control } from 'react-hook-form';
import { Textarea } from '@/components/ui/textarea';
import { FormField, FormItem, FormLabel, FormControl, FormDescription, FormMessage } from '@/components/ui/form';
import type { FieldDef } from '../types';

export function TextField({ def, control }: { def: FieldDef; control: Control }) {
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
            <Textarea {...field} placeholder={def.placeholder} value={field.value ?? ''} rows={3} />
          </FormControl>
          {def.help && <FormDescription>{def.help}</FormDescription>}
          <FormMessage />
        </FormItem>
      )}
    />
  );
}
