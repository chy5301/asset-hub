// frontend/src/features/assets/detail/attachment-grid.tsx
import { FileText, FileImage, File } from "lucide-react";
import { EmptyState } from "@/components/feedback/empty-state";
import { ErrorState } from "@/components/feedback/error-state";
import { Skeleton } from "@/components/ui/skeleton";
import type { components } from "@/api/generated/schema";
import type { UseQueryResult } from "@tanstack/react-query";

type AttachmentRead = components["schemas"]["AttachmentRead"];

interface AttachmentGridProps {
  query: UseQueryResult<AttachmentRead[]>;
  onOpen: (att: AttachmentRead) => void;
}

export function AttachmentGrid({ query, onOpen }: AttachmentGridProps) {
  return (
    <section>
      <h2 className="mb-3 text-lg font-medium">附件</h2>
      {query.isLoading ? (
        <GridSkeleton />
      ) : query.isError ? (
        <ErrorState error={query.error} onRetry={() => query.refetch()} />
      ) : (query.data ?? []).length === 0 ? (
        <EmptyState
          title="暂无附件"
          description="通过登记流程或 asset-hub attachment add CLI 上传。"
        />
      ) : (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
          {(query.data ?? []).map((att) => (
            <button
              key={att.id}
              type="button"
              onClick={() => onOpen(att)}
              className="group relative aspect-square overflow-hidden rounded-md ring-1 ring-border cursor-pointer transition-shadow hover:ring-2 hover:ring-primary/40 focus-visible:ring-2 focus-visible:ring-primary/40"
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
                  <span className="line-clamp-2 text-xs text-center">
                    {att.original_name}
                  </span>
                </div>
              )}
            </button>
          ))}
        </div>
      )}
    </section>
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
