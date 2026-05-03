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
  /** 默认 'block'（垂直堆叠）；'inline' 给 bool 类型用横向布局：control 在左，label/help/message 在右 */
  layout?: 'block' | 'inline';
  /** 写入路径前缀。默认 'custom_data'（写到 custom_data.${def.key}）；'root' 写到顶层 ${def.key}（用于 acquired_at 等通用字段） */
  pathPrefix?: 'custom_data' | 'root';
  children: (
    field: ControllerRenderProps<TFieldValues, Path<TFieldValues>>,
  ) => ReactNode;
};

export function FieldShell<TFieldValues extends FieldValues>({
  def,
  control,
  layout = 'block',
  pathPrefix = 'custom_data',
  children,
}: FieldShellProps<TFieldValues>) {
  const name = (
    pathPrefix === 'root' ? def.key : `custom_data.${def.key}`
  ) as Path<TFieldValues>;
  return (
    <FormField
      control={control}
      name={name}
      render={({ field }) => {
        if (layout === 'inline') {
          return (
            <FormItem className="flex flex-row items-start gap-3 space-y-0">
              <FormControl>{children(field)}</FormControl>
              <div className="space-y-1 leading-none">
                <FormLabel htmlFor={`field-${def.key}`}>
                  {def.label ?? def.key}
                  {def.required && <span className="ml-1 text-destructive">*</span>}
                </FormLabel>
                {def.help && <FormDescription>{def.help}</FormDescription>}
                <FormMessage />
              </div>
            </FormItem>
          );
        }
        return (
          <FormItem>
            <FormLabel htmlFor={`field-${def.key}`}>
              {def.label ?? def.key}
              {def.required && <span className="ml-1 text-destructive">*</span>}
            </FormLabel>
            <FormControl>{children(field)}</FormControl>
            {def.help && <FormDescription>{def.help}</FormDescription>}
            <FormMessage />
          </FormItem>
        );
      }}
    />
  );
}
