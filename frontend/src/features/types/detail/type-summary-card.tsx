import type { components } from '@/api/generated/schema';

type TypeRead = components['schemas']['TypeRead'];

export function TypeSummaryCard({ type }: { type: TypeRead }) {
  return (
    <dl className="grid grid-cols-2 gap-4 text-sm">
      <div>
        <dt className="text-xs uppercase text-muted-foreground">name</dt>
        <dd className="font-medium">{type.name}</dd>
      </div>
      <div>
        <dt className="text-xs uppercase text-muted-foreground">code_prefix</dt>
        <dd className="font-mono">{type.code_prefix}</dd>
      </div>
      <div className="col-span-2">
        <dt className="text-xs uppercase text-muted-foreground">description</dt>
        <dd>{type.description || <span className="text-muted-foreground">—</span>}</dd>
      </div>
      <div>
        <dt className="text-xs uppercase text-muted-foreground">created_at</dt>
        <dd className="text-muted-foreground">{type.created_at}</dd>
      </div>
      <div>
        <dt className="text-xs uppercase text-muted-foreground">updated_at</dt>
        <dd className="text-muted-foreground">{type.updated_at}</dd>
      </div>
    </dl>
  );
}
