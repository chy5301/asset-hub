import { type Control } from 'react-hook-form';
import { DynamicFieldRenderer } from './dynamic-field-renderer';
import type { FieldDef } from './types';

interface CustomFieldsFormProps {
  control: Control;
  fieldDefs: FieldDef[];
  typeName: string;
}

export function CustomFieldsForm({ control, fieldDefs, typeName }: CustomFieldsFormProps) {
  if (fieldDefs.length === 0) {
    return null;
  }
  return (
    <section className="space-y-4">
      <h2 className="text-sm font-semibold uppercase tracking-wide text-foreground border-b pb-1.5">
        {typeName}
        <span className="ml-2 rounded-full bg-secondary px-2 text-xs font-normal">
          {fieldDefs.length} 个字段
        </span>
      </h2>
      <div className="space-y-4">
        {fieldDefs.map((def) => (
          <DynamicFieldRenderer key={def.key} def={def} control={control} />
        ))}
      </div>
    </section>
  );
}
