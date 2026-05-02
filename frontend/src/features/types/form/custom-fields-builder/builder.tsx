import { useFieldArray } from 'react-hook-form';
import type { Control, UseFormSetValue, FieldErrors } from 'react-hook-form';
import { Plus } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { FieldCard } from './field-card';
import type { CreateTypeFormValues, FieldDefFormValue } from '../build-type-schema';

interface Props {
  control: Control<CreateTypeFormValues>;
  setValue: UseFormSetValue<CreateTypeFormValues>;
  errors?: FieldErrors<CreateTypeFormValues>;
}

export function CustomFieldsBuilder({ control, setValue, errors }: Props) {
  const { fields, append, remove, move } = useFieldArray({
    control,
    name: 'custom_fields',
  });

  function handleAdd() {
    append({ key: '', type: 'string', required: false } as FieldDefFormValue);
  }

  if (fields.length === 0) {
    return (
      <button
        type="button"
        onClick={handleAdd}
        aria-label="添加字段"
        className="w-full rounded border border-dashed border-muted-foreground/40 py-12 text-center text-sm text-muted-foreground transition-colors hover:border-primary hover:bg-primary/5 hover:text-primary cursor-pointer"
      >
        <Plus className="inline h-4 w-4 mr-2" />
        添加你的第一个字段
      </button>
    );
  }

  return (
    <div className="space-y-4">
      {/* 外层 space-y-4：字段列表与底部 "+ 添加字段" CTA 之间的间距 */}
      <div className="space-y-4">
        {/* 卡片间距 var(--space-md) = 16px = space-y-4（F6 修订，原 space-y-2 不符 spec §8.1）*/}
        {fields.map((f, idx) => (
          <FieldCard
            key={f.id}
            control={control}
            setValue={setValue}
            index={idx}
            total={fields.length}
            defaultExpanded={idx === fields.length - 1 && f.key === ''}
            onRemove={() => remove(idx)}
            onMoveUp={() => move(idx, idx - 1)}
            onMoveDown={() => move(idx, idx + 1)}
            errors={errors}
          />
        ))}
      </div>
      <Button type="button" variant="outline" onClick={handleAdd}>
        <Plus className="h-4 w-4 mr-2" />
        添加字段
      </Button>
    </div>
  );
}
