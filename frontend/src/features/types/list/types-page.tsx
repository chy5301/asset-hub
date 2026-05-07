import { useState } from 'react';
import { Link } from '@tanstack/react-router';
import { Plus } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { EmptyState } from '@/components/feedback/empty-state';
import { ErrorState } from '@/components/feedback/error-state';
import { useAssetTypesQuery } from '@/api/hooks/types';
import { TypesTable } from './types-table';
import { TypesTableSkeleton } from './types-table-skeleton';
import { TypeDeleteDialog } from '../detail/type-delete-dialog';
import type { TypeRead } from '@/features/assets/types';

export function TypesPage() {
  const q = useAssetTypesQuery();
  const [deletingType, setDeletingType] = useState<TypeRead | null>(null);

  return (
    <div className="space-y-6">
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-xl font-semibold">类型管理</h1>
          {q.data && (
            <p className="text-sm text-muted-foreground">共 {q.data.length} 个类型</p>
          )}
        </div>
        <Button asChild>
          <Link to="/types/new">
            <Plus className="h-4 w-4 mr-2" />
            新建类型
          </Link>
        </Button>
      </div>

      {q.isLoading && <TypesTableSkeleton />}
      {q.isError && <ErrorState error={q.error} onRetry={() => q.refetch()} />}
      {q.data && q.data.length === 0 && (
        <EmptyState
          title="还没有类型"
          description="先创建一个类型，再为该类型登记资产"
          action={
            <Button asChild>
              <Link to="/types/new">创建第一个类型</Link>
            </Button>
          }
        />
      )}
      {q.data && q.data.length > 0 && (
        <TypesTable rows={q.data} onDelete={setDeletingType} bodyKey={String(q.dataUpdatedAt)} />
      )}

      {deletingType && (
        <TypeDeleteDialog
          type={deletingType}
          onClose={() => setDeletingType(null)}
        />
      )}
    </div>
  );
}
