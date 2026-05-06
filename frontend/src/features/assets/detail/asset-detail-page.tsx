import { useState } from "react";
import { useNavigate } from "@tanstack/react-router";

import { useAssetDetailQuery } from "@/api/hooks/assets";
import { useAttachmentsQuery } from "@/api/hooks/attachments";
import { useTypeQuery } from "@/api/hooks/types";
import { ErrorState } from "@/components/feedback/error-state";
import { isHttpError } from "@/lib/error";
import type { FieldDef } from "@/features/assets/form/types";
import type { AttachmentRead } from "@/features/assets/types";

import { AssetHeader } from "./asset-header";
import { AssetNotFound } from "./asset-not-found";
import { AttachmentGrid } from "./attachment-grid";
import { AttachmentLightbox } from "./attachment-lightbox";
import { CustomDataSection } from "./custom-data-section";
import { DeleteAssetAlert } from "./delete-asset-alert";
import { DetailSkeleton } from "./detail-skeleton";
import { GeneralFields } from "./general-fields";
import { TransitionTimeline } from "./transition-timeline";

interface AssetDetailPageProps {
  id: string;
}

export function AssetDetailPage({ id }: AssetDetailPageProps) {
  const navigate = useNavigate();
  const assetQuery = useAssetDetailQuery(id);
  const attachmentsQuery = useAttachmentsQuery(id);
  const typeQuery = useTypeQuery(assetQuery.data?.type_id);

  const [deleteOpen, setDeleteOpen] = useState(false);
  const [lightboxAttachment, setLightboxAttachment] = useState<AttachmentRead | null>(null);

  if (assetQuery.isLoading) return <DetailSkeleton />;

  if (
    assetQuery.isError &&
    isHttpError(assetQuery.error) &&
    assetQuery.error.status === 404
  ) {
    return <AssetNotFound />;
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
  const assetType = typeQuery.data;
  const typeName = asset.type_name ?? undefined;

  return (
    <>
      <title>{`${asset.name} · asset-hub`}</title>
      <main className="mx-auto max-w-[960px] space-y-10 px-4 py-8">
        <AssetHeader
          asset={asset}
          onDelete={() => setDeleteOpen(true)}
        />
        <GeneralFields asset={asset} typeName={typeName} />
        <CustomDataSection
          customData={(asset.custom_data ?? {}) as Record<string, unknown>}
          fieldDefs={(assetType?.custom_fields ?? []) as FieldDef[]}
          assetId={asset.id}
        />
        <AttachmentGrid
          query={attachmentsQuery}
          onOpen={(att) => setLightboxAttachment(att)}
          assetId={asset.id}
        />
        <TransitionTimeline assetId={asset.id} />
      </main>
      <AttachmentLightbox
        attachment={lightboxAttachment}
        assetId={id}
        onClose={() => setLightboxAttachment(null)}
      />
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
