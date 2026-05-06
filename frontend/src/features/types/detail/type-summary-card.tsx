import type { TypeRead } from '@/features/assets/types';
import { formatDateTime } from '@/lib/date';

export function TypeSummaryCard({ type }: { type: TypeRead }) {
  return (
    <dl className="grid grid-cols-2 gap-4 text-sm">
      <div>
        <dt className="text-xs uppercase text-muted-foreground">名称</dt>
        <dd className="font-medium">{type.name}</dd>
      </div>
      <div>
        <dt className="text-xs uppercase text-muted-foreground">代号前缀</dt>
        <dd className="font-mono">{type.code_prefix}</dd>
      </div>
      <div className="col-span-2">
        <dt className="text-xs uppercase text-muted-foreground">描述</dt>
        <dd>{type.description || <span className="text-muted-foreground">—</span>}</dd>
      </div>
      <div>
        <dt className="text-xs uppercase text-muted-foreground">创建时间</dt>
        <dd className="text-muted-foreground">{formatDateTime(type.created_at)}</dd>
      </div>
      <div>
        <dt className="text-xs uppercase text-muted-foreground">更新时间</dt>
        <dd className="text-muted-foreground">{formatDateTime(type.updated_at)}</dd>
      </div>
    </dl>
  );
}
