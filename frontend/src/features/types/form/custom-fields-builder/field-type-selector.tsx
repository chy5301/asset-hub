import type { FieldDefFormValue } from '../build-type-schema';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';

const FIELD_TYPE_OPTIONS: { value: FieldDefFormValue['type']; label: string }[] = [
  { value: 'string', label: 'string · 短文本' },
  { value: 'text', label: 'text · 长文本' },
  { value: 'url', label: 'url · 网址' },
  { value: 'int', label: 'int · 整数' },
  { value: 'float', label: 'float · 小数' },
  { value: 'bool', label: 'bool · 布尔' },
  { value: 'date', label: 'date · 日期' },
  { value: 'enum', label: 'enum · 单选' },
  { value: 'multi-enum', label: 'multi-enum · 多选' },
];

interface Props {
  value: FieldDefFormValue['type'];
  onChange: (next: FieldDefFormValue['type']) => void;
  id?: string;
}

export function FieldTypeSelector({ value, onChange, id }: Props) {
  return (
    <Select value={value} onValueChange={onChange}>
      <SelectTrigger id={id} className="w-[220px]">
        <SelectValue placeholder="选择字段类型" />
      </SelectTrigger>
      <SelectContent className="bg-popover">
        {FIELD_TYPE_OPTIONS.map((opt) => (
          <SelectItem key={opt.value} value={opt.value}>
            {opt.label}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}
