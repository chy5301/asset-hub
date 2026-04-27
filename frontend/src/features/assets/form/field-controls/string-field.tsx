import { type Control } from 'react-hook-form';
import { Input } from '@/components/ui/input';
import { FormField, FormItem, FormLabel, FormControl, FormDescription, FormMessage } from '@/components/ui/form';
import type { FieldDef } from '../types';

export function StringField({ def, control }: { def: FieldDef; control: Control }) {
  return (
    <FormField
      control={control}
      name={def.key}
      render={({ field }) => (
        <FormItem>
          <FormLabel>
            {def.label ?? def.key}
            {def.required && <span className="ml-1 text-destructive">*</span>}
          </FormLabel>
          <FormControl>
            <Input
              {...field}
              placeholder={def.placeholder}
              value={field.value ?? ''}
            />
          </FormControl>
          {def.help && <FormDescription>{def.help}</FormDescription>}
          <FormMessage />
        </FormItem>
      )}
    />
  );
}
