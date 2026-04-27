import { CalendarIcon } from 'lucide-react';
import { format } from 'date-fns';
import { zhCN } from 'date-fns/locale';
import { type Control } from 'react-hook-form';
import { Button } from '@/components/ui/button';
import { Calendar } from '@/components/ui/calendar';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { FormField, FormItem, FormLabel, FormControl, FormDescription, FormMessage } from '@/components/ui/form';
import { cn } from '@/lib/utils';
import type { FieldDef } from '../types';

export function DateField({ def, control }: { def: FieldDef; control: Control }) {
  return (
    <FormField
      control={control}
      name={def.key}
      render={({ field }) => (
        <FormItem className="flex flex-col">
          <FormLabel>
            {def.label ?? def.key}
            {def.required && <span className="ml-1 text-destructive">*</span>}
          </FormLabel>
          <Popover>
            <PopoverTrigger asChild>
              <FormControl>
                <Button
                  variant="outline"
                  className={cn(
                    'w-full justify-start text-left font-normal',
                    !field.value && 'text-muted-foreground',
                  )}
                >
                  <CalendarIcon className="mr-2 h-4 w-4" />
                  {field.value
                    ? format(new Date(field.value), 'yyyy-MM-dd', { locale: zhCN })
                    : (def.placeholder ?? '选择日期')}
                </Button>
              </FormControl>
            </PopoverTrigger>
            <PopoverContent className="w-auto p-0" align="start">
              <Calendar
                mode="single"
                selected={field.value ? new Date(field.value) : undefined}
                onSelect={(d) => field.onChange(d ? format(d, 'yyyy-MM-dd') : '')}
                initialFocus
              />
            </PopoverContent>
          </Popover>
          {def.help && <FormDescription>{def.help}</FormDescription>}
          <FormMessage />
        </FormItem>
      )}
    />
  );
}
