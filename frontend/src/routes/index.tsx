import { createFileRoute } from "@tanstack/react-router";
import { useAssetsQuery } from "@/api/hooks/assets";
import { EmptyState } from "@/components/feedback/empty-state";
import { ErrorState } from "@/components/feedback/error-state";
import { SkeletonRow } from "@/components/feedback/skeleton-row";
import { AssetsFilters } from "@/features/assets/list/assets-filters";
import { assetsSearchSchema } from "@/features/assets/list/search-schema";

export const Route = createFileRoute("/")({
  validateSearch: (search) => assetsSearchSchema.parse(search),
  component: AssetListPage,
});

function AssetListPage() {
  const search = Route.useSearch();
  const query = useAssetsQuery(search);

  return (
    <section className="space-y-4">
      <AssetsFilters search={search} />
      {renderBody()}
    </section>
  );

  function renderBody() {
    if (query.isLoading) {
      return (
        <table className="w-full">
          <tbody>
            <SkeletonRow columns={8} rows={search.pageSize} />
          </tbody>
        </table>
      );
    }
    if (query.isError) {
      return <ErrorState error={query.error} onRetry={() => query.refetch()} />;
    }
    if (!query.data || query.data.length === 0) {
      return <EmptyState />;
    }
    return (
      <p className="text-sm text-muted-foreground">
        共 {query.data.length} 条 —— 表格将在 Task 17 接入
      </p>
    );
  }
}
