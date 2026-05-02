import { useState } from 'react';
import { Link } from '@tanstack/react-router';
import { Inbox, Plus } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { ErrorState } from '@/components/feedback/error-state';
import { useAssetTypesQuery } from '@/api/hooks/types';
import { TypesTable } from './types-table';
import { TypesTableSkeleton } from './types-table-skeleton';
import { TypeDeleteDialog } from '../detail/type-delete-dialog';
import type { components } from '@/api/generated/schema';

type TypeRead = components['schemas']['TypeRead'];

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
        {/* Task 35 将注册 /types/new 路由；此处暂用 as never 绕过路由类型检查 */}
        <Button asChild>
          <Link to="/types/new" params={undefined as never}>
            <Plus className="h-4 w-4 mr-2" />
            新建类型
          </Link>
        </Button>
      </div>

      {q.isLoading && <TypesTableSkeleton />}
      {q.isError && <ErrorState error={q.error} onRetry={() => q.refetch()} />}
      {q.data && q.data.length === 0 && (
        <div className="flex flex-col items-center gap-3 py-16 text-muted-foreground">
          <Inbox className="h-10 w-10" />
          <p>还没有类型</p>
          <Button asChild>
            {/* Task 35 将注册 /types/new 路由；此处暂用 as never 绕过路由类型检查 */}
            <Link to="/types/new" params={undefined as never}>创建第一个类型</Link>
          </Button>
        </div>
      )}
      {q.data && q.data.length > 0 && (
        <TypesTable rows={q.data} onDelete={setDeletingType} />
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
