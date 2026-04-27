import { type Control } from 'react-hook-form';
import { Checkbox } from '@/components/ui/checkbox';
import { FormField, FormItem, FormLabel, FormControl, FormDescription, FormMessage } from '@/components/ui/form';
import type { FieldDef } from '../types';

export function BoolField({ def, control }: { def: FieldDef; control: Control }) {
  return (
    <FormField
      control={control}
      name={`custom_data.${def.key}`}
      render={({ field }) => (
        <FormItem className="flex flex-row items-start gap-3 space-y-0">
          <FormControl>
            <Checkbox
              checked={!!field.value}
              onCheckedChange={field.onChange}
              id={`bool-${def.key}`}
            />
          </FormControl>
          <div className="space-y-1 leading-none">
            <FormLabel htmlFor={`bool-${def.key}`}>
              {def.label ?? def.key}
              {def.required && <span className="ml-1 text-destructive">*</span>}
            </FormLabel>
            {def.help && <FormDescription>{def.help}</FormDescription>}
            <FormMessage />
          </div>
        </FormItem>
      )}
    />
  );
}
