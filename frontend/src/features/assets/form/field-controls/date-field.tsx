import { CalendarIcon } from 'lucide-react';
import { format } from 'date-fns';
import { zhCN } from 'date-fns/locale';
import type { Control, FieldValues } from 'react-hook-form';
import { Button } from '@/components/ui/button';
import { Calendar } from '@/components/ui/calendar';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { cn } from '@/lib/utils';
import { FieldShell } from './field-shell';
import type { FieldDef } from '../types';

export function DateField<TFieldValues extends FieldValues>({
  def,
  control,
  pathPrefix,
}: {
  def: FieldDef;
  control: Control<TFieldValues>;
  pathPrefix?: 'custom_data' | 'root';
}) {
  return (
    <FieldShell def={def} control={control} pathPrefix={pathPrefix}>
      {(field) => (
        <Popover>
          <PopoverTrigger asChild>
            <Button
              id={`field-${def.key}`}
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
      )}
    </FieldShell>
  );
}
