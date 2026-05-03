import type { Control, FieldValues } from 'react-hook-form';
import { SectionCaption } from '@/components/ui/section-heading';
import { DynamicFieldRenderer } from './dynamic-field-renderer';
import type { FieldDef } from './types';

interface CustomFieldsFormProps<TFieldValues extends FieldValues> {
  control: Control<TFieldValues>;
  fieldDefs: FieldDef[];
  typeName: string;
}

export function CustomFieldsForm<TFieldValues extends FieldValues>({
  control,
  fieldDefs,
  typeName,
}: CustomFieldsFormProps<TFieldValues>) {
  if (fieldDefs.length === 0) {
    return null;
  }
  return (
    <section className="space-y-4">
      <SectionCaption>
        {typeName}
        <span className="ml-2 rounded-full bg-secondary px-2 text-xs font-normal">
          {fieldDefs.length} 个字段
        </span>
      </SectionCaption>
      <div className="space-y-4">
        {fieldDefs.map((def) => (
          <DynamicFieldRenderer key={def.key} def={def} control={control} />
        ))}
      </div>
    </section>
  );
}
