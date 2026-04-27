import { type Control } from 'react-hook-form';
import { Input } from '@/components/ui/input';
import { FormField, FormItem, FormLabel, FormControl, FormDescription, FormMessage } from '@/components/ui/form';
import type { FieldDef } from '../types';

export function NumberField({ def, control }: { def: FieldDef; control: Control }) {
  const inputMode = def.type === 'float' ? 'decimal' : 'numeric';
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
            <div className="relative">
              <Input
                type="text"
                inputMode={inputMode}
                {...field}
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
          </FormControl>
          {def.help && <FormDescription>{def.help}</FormDescription>}
          <FormMessage />
        </FormItem>
      )}
    />
  );
}
