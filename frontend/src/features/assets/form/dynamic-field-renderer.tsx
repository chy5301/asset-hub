import { type Control } from 'react-hook-form';
import { StringField } from './field-controls/string-field';
import { TextField } from './field-controls/text-field';
import { NumberField } from './field-controls/number-field';
import { BoolField } from './field-controls/bool-field';
import { DateField } from './field-controls/date-field';
import { EnumField } from './field-controls/enum-field';
import { MultiEnumField } from './field-controls/multi-enum-field';
import { UrlField } from './field-controls/url-field';
import type { FieldDef } from './types';

export function DynamicFieldRenderer({ def, control }: { def: FieldDef; control: Control }) {
  switch (def.type) {
    case 'string': return <StringField def={def} control={control} />;
    case 'text': return <TextField def={def} control={control} />;
    case 'int': case 'float': return <NumberField def={def} control={control} />;
    case 'bool': return <BoolField def={def} control={control} />;
    case 'date': return <DateField def={def} control={control} />;
    case 'enum': return <EnumField def={def} control={control} />;
    case 'multi-enum': return <MultiEnumField def={def} control={control} />;
    case 'url': return <UrlField def={def} control={control} />;
  }
}
