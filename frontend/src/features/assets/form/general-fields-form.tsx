import type { Control, FieldValues, Path } from 'react-hook-form';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { FormField, FormItem, FormLabel, FormControl, FormDescription, FormMessage } from '@/components/ui/form';
import { DateField } from './field-controls/date-field';
import type { components } from '@/api/generated/schema';

type AssetTypeRead = components['schemas']['TypeRead'];

interface GeneralFieldsFormProps<TFieldValues extends FieldValues> {
  control: Control<TFieldValues>;
  types: AssetTypeRead[];
  /** 编辑模式下 type 字段 disabled */
  typeReadonly: boolean;
  /** 编辑模式下显示只读 asset_code */
  assetCode?: string;
  /** 编辑模式下 type select 用 prop 传，绕过 useWatch（type_id 不在 form values） */
  forceTypeName?: string;
}

export function GeneralFieldsForm<TFieldValues extends FieldValues>({
  control,
  types,
  typeReadonly,
  assetCode,
  forceTypeName,
}: GeneralFieldsFormProps<TFieldValues>) {
  // CreateFormValues / EditFormValues 都含这些 base 字段；用 Path<TFieldValues> 包一层
  // 让 RHF 在不知道具体 TFieldValues 时仍然接受字面量名。
  const nameField = 'name' as Path<TFieldValues>;
  const typeIdField = 'type_id' as Path<TFieldValues>;
  const serialField = 'serial_number' as Path<TFieldValues>;
  const holderField = 'holder' as Path<TFieldValues>;
  const locationField = 'location' as Path<TFieldValues>;
  const notesField = 'notes' as Path<TFieldValues>;

  return (
    <div className="space-y-4">
      {assetCode && (
        <FormItem>
          <FormLabel>编号</FormLabel>
          <FormControl>
            <Input value={assetCode} readOnly disabled className="font-code bg-muted" />
          </FormControl>
          <FormDescription>系统自动生成，创建后不可改</FormDescription>
        </FormItem>
      )}

      <FormField
        control={control}
        name={nameField}
        render={({ field }) => (
          <FormItem>
            <FormLabel>资产名 <span className="text-destructive">*</span></FormLabel>
            <FormControl><Input {...field} placeholder="如 ThinkPad X1 Carbon" /></FormControl>
            <FormMessage />
          </FormItem>
        )}
      />

      {typeReadonly && forceTypeName !== undefined ? (
        <FormItem>
          <FormLabel>
            资产类型 <span className="text-destructive">*</span>
            <span className="ml-2 text-xs text-muted-foreground">创建后不可改</span>
          </FormLabel>
          <FormControl>
            <Input value={forceTypeName} readOnly disabled className="bg-muted" />
          </FormControl>
        </FormItem>
      ) : (
        <FormField
          control={control}
          name={typeIdField}
          render={({ field }) => (
            <FormItem>
              <FormLabel>资产类型 <span className="text-destructive">*</span></FormLabel>
              <Select value={field.value ?? ''} onValueChange={field.onChange}>
                <FormControl>
                  <SelectTrigger><SelectValue placeholder="请选择类型" /></SelectTrigger>
                </FormControl>
                <SelectContent>
                  {types.map((t) => (
                    <SelectItem key={t.id} value={t.id}>
                      {t.name} <span className="ml-2 font-code text-xs text-muted-foreground">{t.code_prefix}</span>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <FormMessage />
            </FormItem>
          )}
        />
      )}

      <FormField
        control={control}
        name={serialField}
        render={({ field }) => (
          <FormItem>
            <FormLabel>SN</FormLabel>
            <FormControl><Input {...field} value={field.value ?? ''} placeholder="厂家铭牌编号（可空）" className="font-code" /></FormControl>
            <FormMessage />
          </FormItem>
        )}
      />

      <DateField
        control={control}
        def={{
          key: 'acquired_at', label: '入账日期', type: 'date',
          help: '业务意义的入账日期；不知道时不填',
        }}
      />

      <FormField
        control={control}
        name={holderField}
        render={({ field }) => (
          <FormItem>
            <FormLabel>持有人</FormLabel>
            <FormControl><Input {...field} value={field.value ?? ''} placeholder="可空" /></FormControl>
            <FormMessage />
          </FormItem>
        )}
      />

      <FormField
        control={control}
        name={locationField}
        render={({ field }) => (
          <FormItem>
            <FormLabel>位置</FormLabel>
            <FormControl><Input {...field} value={field.value ?? ''} placeholder="可空" /></FormControl>
            <FormMessage />
          </FormItem>
        )}
      />

      <FormField
        control={control}
        name={notesField}
        render={({ field }) => (
          <FormItem>
            <FormLabel>备注</FormLabel>
            <FormControl><Textarea {...field} value={field.value ?? ''} rows={3} placeholder="可空" /></FormControl>
            <FormMessage />
          </FormItem>
        )}
      />
    </div>
  );
}
