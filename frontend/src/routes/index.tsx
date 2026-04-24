import { useEffect, useMemo } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { useAssetsQuery } from "@/api/hooks/assets";
import { useAssetTypesQuery } from "@/api/hooks/types";
import { EmptyState } from "@/components/feedback/empty-state";
import { ErrorState } from "@/components/feedback/error-state";
import { SkeletonRow } from "@/components/feedback/skeleton-row";
import { AssetsFilters } from "@/features/assets/list/assets-filters";
import { AssetsPagination } from "@/features/assets/list/assets-pagination";
import { AssetsTable, type AssetRow } from "@/features/assets/list/assets-table";
import {
  ColumnVisibilityMenu,
  useColumnVisibility,
} from "@/features/assets/list/column-visibility";
import { assetsSearchSchema } from "@/features/assets/list/search-schema";

const WARN_THRESHOLD = 2000;

export const Route = createFileRoute("/")({
  validateSearch: (search) => assetsSearchSchema.parse(search),
  component: AssetListPage,
});

function AssetListPage() {
  const search = Route.useSearch();
  const query = useAssetsQuery(search);
  const typesQuery = useAssetTypesQuery();
  const { visible, toggle } = useColumnVisibility();

  const typeNameById = useMemo(() => {
    const map: Record<string, string> = {};
    for (const t of typesQuery.data ?? []) {
      if (t && typeof t === "object" && "id" in t && "name" in t) {
        map[t.id as string] = t.name as string;
      }
    }
    return map;
  }, [typesQuery.data]);

  useEffect(() => {
    if (query.data && query.data.length > WARN_THRESHOLD) {
      console.warn(
        `asset count ${query.data.length} exceeds client-paginate threshold (${WARN_THRESHOLD}); consider server-side pagination`,
      );
    }
  }, [query.data]);

  const bodyKey = useMemo(
    () => JSON.stringify({ s: search, v: visible }),
    [search, visible],
  );

  return (
    <section className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <AssetsFilters search={search} />
        <ColumnVisibilityMenu visible={visible} onToggle={toggle} />
      </div>

      {renderBody()}
    </section>
  );

  function renderBody() {
    if (query.isLoading) {
      return (
        <div className="overflow-x-auto rounded-sm border border-border">
          <table className="w-full">
            <tbody>
              <SkeletonRow columns={8} rows={Math.min(search.pageSize, 10)} />
            </tbody>
          </table>
        </div>
      );
    }
    if (query.isError) {
      return <ErrorState error={query.error} onRetry={() => query.refetch()} />;
    }
    if (!query.data || query.data.length === 0) {
      return <EmptyState />;
    }

    const rows = query.data as AssetRow[];
    return (
      <>
        <AssetsTable
          rows={rows}
          search={search}
          visible={visible}
          typeNameById={typeNameById}
          bodyKey={bodyKey}
        />
        <AssetsPagination search={search} total={rows.length} />
      </>
    );
  }
}
