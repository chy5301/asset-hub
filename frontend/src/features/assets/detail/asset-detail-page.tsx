import { useMemo, useState } from "react";
import { useNavigate } from "@tanstack/react-router";
import { toast } from "sonner";
import {
  useAssetDetailQuery,
  useChangeAssetStatusMutation,
} from "@/api/hooks/assets";
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
import { StateChangeAlert } from "./state-change-alert";
import { DeleteAssetAlert } from "./delete-asset-alert";
import {
  STATE_CHANGE_ACTIONS,
  type StateChangeKey,
} from "./state-change-actions";
import { isHttpError, toFriendlyMessage } from "@/lib/error";
import type { components } from "@/api/generated/schema";

interface AssetDetailPageProps {
  id: string;
}

export function AssetDetailPage({ id }: AssetDetailPageProps) {
  const navigate = useNavigate();
  const assetQuery = useAssetDetailQuery(id);
  const historyQuery = useCheckoutHistoryQuery(id);
  const attachmentsQuery = useAttachmentsQuery(id);
  const typesQuery = useAssetTypesQuery();

  const currentCheckout = useMemo(
    () => deriveCurrentCheckout(historyQuery.data, assetQuery.data?.current_checkout_id),
    [historyQuery.data, assetQuery.data?.current_checkout_id],
  );

  const [checkoutOpen, setCheckoutOpen] = useState(false);
  const [returnOpen, setReturnOpen] = useState(false);
  const [stateChangeKey, setStateChangeKey] = useState<StateChangeKey | null>(
    null,
  );
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [lightboxAttachment, setLightboxAttachment] = useState<
    components["schemas"]["AttachmentRead"] | null
  >(null);

  const changeStatusMutation = useChangeAssetStatusMutation(id);

  async function handleStateChange(key: StateChangeKey) {
    const action = STATE_CHANGE_ACTIONS[key];
    if (action.needsConfirm) {
      setStateChangeKey(key);
    } else {
      try {
        await changeStatusMutation.mutateAsync(action.toStatus);
        toast.success(`${action.verb}成功`);
      } catch (err) {
        toast.error(toFriendlyMessage(err));
      }
    }
  }

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
          currentCheckout={currentCheckout}
          onCheckout={() => setCheckoutOpen(true)}
          onReturn={() => setReturnOpen(true)}
          onChangeStatus={handleStateChange}
          onDelete={() => setDeleteOpen(true)}
        />
        <GeneralFields asset={asset} typeName={typeName} />
        <CustomFields asset={asset} assetType={assetType} />
        <AttachmentGrid
          query={attachmentsQuery}
          onOpen={(att) => setLightboxAttachment(att)}
          assetId={asset.id}
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
      {stateChangeKey && (
        <StateChangeAlert
          open
          onOpenChange={(o) => !o && setStateChangeKey(null)}
          asset={asset}
          actionKey={stateChangeKey}
        />
      )}
      <DeleteAssetAlert
        open={deleteOpen}
        onOpenChange={setDeleteOpen}
        asset={{ id: asset.id, name: asset.name, asset_code: asset.asset_code }}
        onDeleted={() =>
          navigate({
            to: "/",
            search: { sort: "asset_code", page: 1, pageSize: 50 },
          })
        }
      />
    </>
  );
}
