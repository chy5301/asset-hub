import { createFileRoute } from "@tanstack/react-router";
import { useAssetsQuery } from "@/api/hooks/assets";
import { EmptyState } from "@/components/feedback/empty-state";
import { ErrorState } from "@/components/feedback/error-state";
import { SkeletonRow } from "@/components/feedback/skeleton-row";
import { assetsSearchSchema } from "@/features/assets/list/search-schema";

export const Route = createFileRoute("/")({
  validateSearch: (search) => assetsSearchSchema.parse(search),
  component: AssetListPage,
});

function AssetListPage() {
  const search = Route.useSearch();
  const query = useAssetsQuery(search);

  if (query.isLoading) {
    return (
      <section>
        <h2 className="sr-only">资产列表</h2>
        <table className="w-full">
          <tbody>
            <SkeletonRow columns={8} rows={search.pageSize} />
          </tbody>
        </table>
      </section>
    );
  }

  if (query.isError) {
    return <ErrorState error={query.error} onRetry={() => query.refetch()} />;
  }

  if (!query.data || query.data.length === 0) {
    return <EmptyState />;
  }

  return (
    <section>
      <h2 className="text-lg font-medium">资产列表（骨架）</h2>
      <p className="mt-1 text-sm text-muted-foreground">
        共 {query.data.length} 条 —— 表格与筛选将在后续 Task 接入
      </p>
    </section>
  );
}
