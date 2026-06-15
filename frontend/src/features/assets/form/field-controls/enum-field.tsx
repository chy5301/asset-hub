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
            选项数>4（走 Select）的 enum 字段不回显已存值。修法分三处，各自必需：
            1. children：不传 children 时 Radix 触发器文字靠「被选中 SelectItem 的文本回灌
               portal」，该 portal 对「挂载后才变更的受控 value」不回灌。传 children 让文字成为
               field.value 的纯函数（enum 选项 value===label，故 field.value 即显示文本）。
               注：value===label 是本调用处才知道的信息，故修在这里而非通用的 Select 包装层。
            2. key：value 变更时 Radix 触发器子树不重渲染重读 context.value（实测 children 单独
               无效，触发器停在挂载时的空值）。key={value} 让 Select 在 value 变化时重挂载、以
               最新 value 全新渲染。空值时 Radix 仍按 value 走 placeholder。
            3. onValueChange 里手动恢复焦点：key 重挂载有副作用 —— 用户在下拉里选值后，Radix
               关闭弹层时的焦点回归（onUnmountAutoFocus，setTimeout(0)）打到的是已被 key 卸载的
               旧 trigger 节点，焦点掉到 document.body。这里把焦点还给重挂后的同 id 触发器，保持
               键盘焦点连续。（程序化 reset 那次重挂载发生在用户交互前，不涉及焦点。）
          */
          <Select
            key={field.value ?? ''}
            value={field.value ?? ''}
            onValueChange={(v) => {
              field.onChange(v);
              requestAnimationFrame(() =>
                document.getElementById(`field-${def.key}`)?.focus(),
              );
            }}
          >
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
