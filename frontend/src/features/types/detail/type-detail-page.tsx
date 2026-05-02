import { useState } from 'react';
import { Link, useNavigate } from '@tanstack/react-router';
import { SearchX, Trash2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { ErrorState } from '@/components/feedback/error-state';
import { Skeleton } from '@/components/ui/skeleton';
import { isHttpError } from '@/lib/error';
import { useTypeQuery } from '@/api/hooks/types';
import { TypeSummaryCard } from './type-summary-card';
import { TypeDeleteDialog } from './type-delete-dialog';
import { TypeForm } from '../form/type-form';

export function TypeDetailPage({ id }: { id: string }) {
  const navigate = useNavigate();
  const q = useTypeQuery(id);
  const [deleting, setDeleting] = useState(false);

  if (q.isLoading) return <Skeleton className="h-96 w-full" />;
  if (q.isError) {
    const is404 = isHttpError(q.error) && q.error.status === 404;
    if (is404) {
      return (
        <div className="flex flex-col items-center gap-3 py-16 text-muted-foreground">
          <SearchX className="h-10 w-10" />
          <p>该类型不存在</p>
          <Button asChild variant="outline">
            <Link to="/types">返回类型列表</Link>
          </Button>
        </div>
      );
    }
    return <ErrorState error={q.error} onRetry={() => q.refetch()} />;
  }
  if (!q.data) return null;

  return (
    <div className="space-y-10">
      <div className="flex items-start justify-between">
        <h1 className="text-xl font-semibold">编辑类型 - {q.data.name}</h1>
        <Button variant="ghost" onClick={() => setDeleting(true)} className="text-destructive">
          <Trash2 className="h-4 w-4 mr-2" />
          删除类型
        </Button>
      </div>

      <section>
        <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground mb-3">
          元信息
        </h2>
        <TypeSummaryCard type={q.data} />
      </section>

      <TypeForm
        mode="edit"
        initial={q.data}
        // useUpdateTypeMutation.onSuccess 已 invalidate qk.assetTypes.detail；自动 refetch
        onSuccess={() => {}}
      />

      {deleting && (
        <TypeDeleteDialog
          type={q.data}
          onClose={() => setDeleting(false)}
          onDeleted={() => navigate({ to: '/types' })}
        />
      )}
    </div>
  );
}
