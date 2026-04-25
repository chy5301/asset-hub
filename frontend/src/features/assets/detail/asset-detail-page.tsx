import { useMemo, useState } from "react";
import { useAssetDetailQuery } from "@/api/hooks/assets";
import { useCheckoutHistoryQuery } from "@/api/hooks/checkouts";
import { useAttachmentsQuery } from "@/api/hooks/attachments";
import { useAssetTypesQuery } from "@/api/hooks/types";
import { ErrorState } from "@/components/feedback/error-state";
import { AssetHeader } from "./asset-header";
import { GeneralFields } from "./general-fields";
import { CustomFields } from "./custom-fields";
import { AttachmentGrid } from "./attachment-grid";
import { CheckoutTimeline } from "./checkout-timeline";
import { deriveCurrentCheckout } from "./current-checkout";
import { DetailSkeleton } from "./detail-skeleton";
import { NotFoundPanel } from "./not-found-panel";
import { AttachmentLightbox } from "./attachment-lightbox";
import { CheckoutDialog } from "./checkout-dialog";
import { ReturnDialog } from "./return-dialog";
import { isHttpError } from "@/lib/error";
import type { components } from "@/api/generated/schema";

interface AssetDetailPageProps {
  id: string;
}

export function AssetDetailPage({ id }: AssetDetailPageProps) {
  const assetQuery = useAssetDetailQuery(id);
  const historyQuery = useCheckoutHistoryQuery(id);
  const attachmentsQuery = useAttachmentsQuery(id);
  const typesQuery = useAssetTypesQuery();

  const currentCheckout = useMemo(
    () => deriveCurrentCheckout(historyQuery.data),
    [historyQuery.data],
  );

  const [checkoutOpen, setCheckoutOpen] = useState(false);
  const [returnOpen, setReturnOpen] = useState(false);
  const [lightboxAttachment, setLightboxAttachment] = useState<
    components["schemas"]["AttachmentRead"] | null
  >(null);

  if (assetQuery.isLoading) return <DetailSkeleton />;

  if (
    assetQuery.isError &&
    isHttpError(assetQuery.error) &&
    assetQuery.error.status === 404
  ) {
    return <NotFoundPanel />;
  }

  if (assetQuery.isError || !assetQuery.data) {
    return (
      <ErrorState
        error={assetQuery.error}
        onRetry={() => assetQuery.refetch()}
      />
    );
  }

  const asset = assetQuery.data;
  const assetType = typesQuery.data?.find((t) => t.id === asset.type_id);
  const typeName = assetType?.name;

  return (
    <>
      <title>{`${asset.name} · asset-hub`}</title>
      <main className="mx-auto max-w-[960px] space-y-10 px-4 py-8">
        <AssetHeader
          asset={asset}
          typeName={typeName}
          currentCheckout={currentCheckout}
          onCheckout={() => setCheckoutOpen(true)}
          onReturn={() => setReturnOpen(true)}
        />
        <GeneralFields asset={asset} typeName={typeName} />
        <CustomFields asset={asset} assetType={assetType} />
        <AttachmentGrid
          query={attachmentsQuery}
          onOpen={(att) => setLightboxAttachment(att)}
        />
        <CheckoutTimeline query={historyQuery} />
      </main>
      <AttachmentLightbox
        attachment={lightboxAttachment}
        assetId={id}
        onClose={() => setLightboxAttachment(null)}
      />
      <CheckoutDialog
        open={checkoutOpen}
        onOpenChange={setCheckoutOpen}
        assetId={id}
      />
      <ReturnDialog
        open={returnOpen}
        onOpenChange={setReturnOpen}
        assetId={id}
        currentCheckout={currentCheckout}
      />
    </>
  );
}
