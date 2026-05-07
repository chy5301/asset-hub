import { FileText, FileImage, File } from "lucide-react";
import { ErrorState } from "@/components/feedback/error-state";
import { Skeleton } from "@/components/ui/skeleton";
import type { AttachmentRead } from "@/features/assets/types";
import type { UseQueryResult } from "@tanstack/react-query";
import { AttachmentAddSlot } from "./attachment-add-slot";

interface AttachmentGridProps {
  query: UseQueryResult<AttachmentRead[]>;
  onOpen: (att: AttachmentRead) => void;
  assetId: string;
}

export function AttachmentGrid({ query, onOpen, assetId }: AttachmentGridProps) {
  return (
    <section>
      <h2 className="mb-3 text-lg font-medium">
        附件{" "}
        {query.data && (
          <span className="text-sm font-normal text-muted-foreground">
            {query.data.length}
          </span>
        )}
      </h2>
      {query.isLoading ? (
        <GridSkeleton />
      ) : query.isError ? (
        <ErrorState error={query.error} onRetry={() => query.refetch()} />
      ) : (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
          {(query.data ?? []).map((att) => (
            <AttachmentTile key={att.id} att={att} onOpen={onOpen} />
          ))}
          <AttachmentAddSlot assetId={assetId} />
        </div>
      )}
    </section>
  );
}

function AttachmentTile({
  att,
  onOpen,
}: {
  att: AttachmentRead;
  onOpen: (a: AttachmentRead) => void;
}) {
  return (
    <button
      type="button"
      onClick={() => onOpen(att)}
      className="group relative aspect-square overflow-hidden rounded-md ring-1 ring-border cursor-pointer transition-all hover:ring-2 hover:ring-primary/40 focus-visible:ring-2 focus-visible:ring-primary/40"
      aria-label={`查看附件 ${att.original_name}`}
    >
      {att.mime_type.startsWith("image/") ? (
        <img
          src={`/api/attachments/${att.id}/content`}
          alt=""
          loading="lazy"
          className="h-full w-full object-cover"
        />
      ) : (
        <div className="flex h-full w-full flex-col items-center justify-center gap-2 bg-muted/30 p-2 text-muted-foreground">
          <KindIcon mime={att.mime_type} />
          <span className="line-clamp-2 text-xs text-center">{att.original_name}</span>
        </div>
      )}
    </button>
  );
}

function KindIcon({ mime }: { mime: string }) {
  if (mime === "application/pdf" || mime.includes("document")) {
    return <FileText className="h-6 w-6" aria-hidden />;
  }
  if (mime.startsWith("image/")) {
    return <FileImage className="h-6 w-6" aria-hidden />;
  }
  return <File className="h-6 w-6" aria-hidden />;
}

function GridSkeleton() {
  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
      {Array.from({ length: 4 }).map((_, i) => (
        <Skeleton key={i} className="aspect-square w-full rounded-md" />
      ))}
    </div>
  );
}
