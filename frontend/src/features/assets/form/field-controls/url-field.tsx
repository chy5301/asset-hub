import { type Control } from 'react-hook-form';
import { Input } from '@/components/ui/input';
import { FormField, FormItem, FormLabel, FormControl, FormDescription, FormMessage } from '@/components/ui/form';
import type { FieldDef } from '../types';

export function UrlField({ def, control }: { def: FieldDef; control: Control }) {
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
            <Input type="url" {...field} placeholder={def.placeholder ?? 'https://…'} value={field.value ?? ''} />
          </FormControl>
          {def.help && <FormDescription>{def.help}</FormDescription>}
          <FormMessage />
        </FormItem>
      )}
    />
  );
}
