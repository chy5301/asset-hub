import type { ReactNode } from 'react';
import type { Control, ControllerRenderProps, FieldValues, Path } from 'react-hook-form';
import {
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form';
import type { FieldDef } from '../types';

type FieldShellProps<TFieldValues extends FieldValues> = {
  def: FieldDef;
  control: Control<TFieldValues>;
  /** 默认 'block'（垂直堆叠）；'inline' 给 bool 类型用横向布局 */
  layout?: 'block' | 'inline';
  children: (
    field: ControllerRenderProps<TFieldValues, Path<TFieldValues>>,
  ) => ReactNode;
};

export function FieldShell<TFieldValues extends FieldValues>({
  def,
  control,
  layout = 'block',
  children,
}: FieldShellProps<TFieldValues>) {
  const name = `custom_data.${def.key}` as Path<TFieldValues>;
  return (
    <FormField
      control={control}
      name={name}
      render={({ field }) => (
        <FormItem
          className={
            layout === 'inline'
              ? 'flex flex-row items-start gap-3 space-y-0'
              : undefined
          }
        >
          <FormLabel htmlFor={`field-${def.key}`}>
            {def.label ?? def.key}
            {def.required && <span className="ml-1 text-destructive">*</span>}
          </FormLabel>
          <FormControl>{children(field)}</FormControl>
          {def.help && <FormDescription>{def.help}</FormDescription>}
          <FormMessage />
        </FormItem>
      )}
    />
  );
}
