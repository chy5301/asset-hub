import { useState } from 'react';
import { useNavigate } from '@tanstack/react-router';
import { Trash2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { ErrorState } from '@/components/feedback/error-state';
import { Skeleton } from '@/components/ui/skeleton';
import { isHttpError } from '@/lib/error';
import { useTypeQuery } from '@/api/hooks/types';
import { SectionCaption } from '@/components/ui/section-heading';
import { TypeSummaryCard } from './type-summary-card';
import { TypeDeleteDialog } from './type-delete-dialog';
import { TypeNotFound } from './type-not-found';
import { TypeForm } from '../form/type-form';

export function TypeDetailPage({ id }: { id: string }) {
  const navigate = useNavigate();
  const q = useTypeQuery(id);
  const [deleting, setDeleting] = useState(false);

  if (q.isLoading) return <Skeleton className="h-96 w-full" />;
  if (q.isError) {
    const is404 = isHttpError(q.error) && q.error.status === 404;
    if (is404) return <TypeNotFound />;
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
        <SectionCaption className="text-muted-foreground mb-3">元信息</SectionCaption>
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
