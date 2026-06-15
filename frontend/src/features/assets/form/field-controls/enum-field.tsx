import type { Control, FieldValues } from 'react-hook-form';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Label } from '@/components/ui/label';
import { FieldShell } from './field-shell';
import { ENUM_INLINE_THRESHOLD, type FieldDef } from '../types';

export function EnumField<TFieldValues extends FieldValues>({
  def,
  control,
}: {
  def: FieldDef;
  control: Control<TFieldValues>;
}) {
  const options = def.options ?? [];
  const useRadio = def.displayAs === 'radio' || (def.displayAs !== 'select' && options.length <= ENUM_INLINE_THRESHOLD);

  return (
    <FieldShell def={def} control={control}>
      {(field) =>
        useRadio ? (
          <RadioGroup
            value={field.value ?? ''}
            onValueChange={field.onChange}
            className="flex flex-col gap-2"
            id={`field-${def.key}`}
          >
            {options.map((opt) => (
              <div key={opt} className="flex items-center gap-2">
                <RadioGroupItem value={opt} id={`${def.key}-${opt}`} />
                <Label htmlFor={`${def.key}-${opt}`} className="font-normal">{opt}</Label>
              </div>
            ))}
          </RadioGroup>
        ) : (
          /*
            issue #39：编辑页「空值挂载 → useEffect 里 form.reset 程序化写入已有值」的时序下，
            选项数>4（走 Select）的 enum 字段不回显已存值。两点根因叠加：
            1. 不传 children 时 Radix 触发器文字靠「被选中 SelectItem 的文本回灌 portal」，
               该 portal 对「挂载后才变更的受控 value」不回灌。传 children 让文字成为
               field.value 的纯函数（enum 选项 value===label，故 field.value 即显示文本）。
            2. 仅传 children 仍不够：value 变更时 Radix 触发器子树不会重渲染重读 context.value，
               故 SelectValue 一直停在挂载时的空值。用 key={field.value} 让整个 Select 在 value
               变化时重挂载，以最新 value 全新渲染。空值时 Radix 仍按 value 走 placeholder。
          */
          <Select key={field.value ?? ''} value={field.value ?? ''} onValueChange={field.onChange}>
            <SelectTrigger id={`field-${def.key}`}>
              <SelectValue placeholder={def.placeholder ?? '请选择'}>
                {field.value ?? ''}
              </SelectValue>
            </SelectTrigger>
            <SelectContent>
              {options.map((opt) => (
                <SelectItem key={opt} value={opt}>{opt}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        )
      }
    </FieldShell>
  );
}
