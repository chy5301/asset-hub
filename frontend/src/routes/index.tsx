import { useCallback, useEffect, useMemo, useState } from "react";
import { createFileRoute, Link } from "@tanstack/react-router";
import { Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useAssetsQuery } from "@/api/hooks/assets";
import { useCheckoutHistoryQuery } from "@/api/hooks/checkouts";
import { EmptyState } from "@/components/feedback/empty-state";
import { ErrorState } from "@/components/feedback/error-state";
import { SkeletonRow } from "@/components/feedback/skeleton-row";
import { CheckoutDialog } from "@/features/assets/detail/checkout-dialog";
import { deriveCurrentCheckout } from "@/features/assets/detail/current-checkout";
import { DeleteAssetAlert } from "@/features/assets/detail/delete-asset-alert";
import { ReturnDialog } from "@/features/assets/detail/return-dialog";
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
  const { visible, toggle } = useColumnVisibility();

  // Dialog state for ⋯ menu actions
  const [checkoutRow, setCheckoutRow] = useState<AssetRow | null>(null);
  const [returnRow, setReturnRow] = useState<AssetRow | null>(null);
  const [deleteRow, setDeleteRow] = useState<AssetRow | null>(null);

  const handleCheckout = useCallback((row: AssetRow) => setCheckoutRow(row), []);
  const handleReturn = useCallback((row: AssetRow) => setReturnRow(row), []);
  const handleDelete = useCallback((row: AssetRow) => setDeleteRow(row), []);

  // 当 ReturnDialog 打开时挂 history query 以拿到 holder/checked_out_at 等回填字段
  const returnHistoryQuery = useCheckoutHistoryQuery(returnRow?.id);
  const currentCheckoutForReturn = deriveCurrentCheckout(
    returnHistoryQuery.data,
    returnRow?.current_checkout_id,
  );

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
    <>
      <section className="space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <AssetsFilters search={search} />
          <div className="flex items-center gap-2">
            <ColumnVisibilityMenu visible={visible} onToggle={toggle} />
            <Link to="/assets/new">
              <Button>
                <Plus className="mr-2 h-4 w-4" />
                登记资产
              </Button>
            </Link>
          </div>
        </div>

        {renderBody()}
      </section>

      <CheckoutDialog
        open={!!checkoutRow}
        onOpenChange={(v) => !v && setCheckoutRow(null)}
        assetId={checkoutRow?.id ?? ""}
      />
      <ReturnDialog
        open={!!returnRow}
        onOpenChange={(v) => !v && setReturnRow(null)}
        assetId={returnRow?.id ?? ""}
        currentCheckout={currentCheckoutForReturn}
      />
      {deleteRow && (
        <DeleteAssetAlert
          open
          onOpenChange={(o) => !o && setDeleteRow(null)}
          asset={{
            id: deleteRow.id,
            name: deleteRow.name,
            asset_code: deleteRow.asset_code,
          }}
        />
      )}
    </>
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
      return (
        <EmptyState
          title="暂无资产"
          description="还没有登记任何资产。可以通过 CLI 登记：asset-hub asset register"
        />
      );
    }

    const rows = query.data as AssetRow[];
    return (
      <>
        <AssetsTable
          rows={rows}
          search={search}
          visible={visible}
          bodyKey={bodyKey}
          onCheckout={handleCheckout}
          onReturn={handleReturn}
          onDelete={handleDelete}
        />
        <AssetsPagination search={search} total={rows.length} />
      </>
    );
  }
}
