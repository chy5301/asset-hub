import { useAssetDetailQuery } from "@/api/hooks/assets";
import { useCheckoutHistoryQuery } from "@/api/hooks/checkouts";
import { useAttachmentsQuery } from "@/api/hooks/attachments";
import { useAssetTypesQuery } from "@/api/hooks/types";
import { ErrorState } from "@/components/feedback/error-state";
import { DetailSkeleton } from "./detail-skeleton";
import { NotFoundPanel } from "./not-found-panel";
import { isHttpError } from "@/lib/error";

interface AssetDetailPageProps {
  id: string;
}

export function AssetDetailPage({ id }: AssetDetailPageProps) {
  const assetQuery = useAssetDetailQuery(id);
  const historyQuery = useCheckoutHistoryQuery(id);
  const attachmentsQuery = useAttachmentsQuery(id);
  const typesQuery = useAssetTypesQuery();

  if (assetQuery.isLoading) return <DetailSkeleton />;

  if (
    assetQuery.isError &&
    isHttpError(assetQuery.error) &&
    assetQuery.error.status === 404
  ) {
    return <NotFoundPanel />;
  }

  if (assetQuery.isError) {
    return (
      <ErrorState
        error={assetQuery.error}
        onRetry={() => assetQuery.refetch()}
      />
    );
  }

  if (!assetQuery.data) return <DetailSkeleton />;

  const asset = assetQuery.data;
  const assetType = (typesQuery.data ?? []).find((t) => t.id === asset.type_id);

  return (
    <>
      <title>{`${asset.name} · asset-hub`}</title>
      <main className="mx-auto max-w-[960px] space-y-10 px-4 py-8">
        {/* Task 9-16 填充各区块；先占位 */}
        <div className="text-sm text-muted-foreground">
          占位：{asset.name} / {asset.id}
          {assetType ? ` / ${assetType.name}` : ""}
          {historyQuery.isLoading ? " / history 加载中" : ""}
          {attachmentsQuery.isLoading ? " / attachments 加载中" : ""}
        </div>
      </main>
    </>
  );
}
