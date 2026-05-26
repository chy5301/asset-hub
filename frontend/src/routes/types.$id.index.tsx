import { useState } from "react";
import { createFileRoute, useNavigate } from "@tanstack/react-router";

import { useTypeQuery } from "@/api/hooks/types";
import { ErrorState } from "@/components/feedback/error-state";
import { Skeleton } from "@/components/ui/skeleton";
import { isHttpError } from "@/lib/error";
import { TypeDetailView } from "@/features/types/detail/type-detail-view";
import { TypeDeleteDialog } from "@/features/types/detail/type-delete-dialog";
import { TypeNotFound } from "@/features/types/detail/type-not-found";

function TypeDetailRoute() {
  const { id } = Route.useParams();
  const navigate = useNavigate();
  const q = useTypeQuery(id);
  const [deleting, setDeleting] = useState(false);

  if (q.isLoading) return <Skeleton className="h-96 w-full" />;
  if (q.isError) {
    const is404 = isHttpError(q.error) && q.error.status === 404;
    if (is404) return <TypeNotFound />;
    return <ErrorState error={q.error} onRetry={() => q.refetch()} />;
  }
  if (!q.data) return null;

  return (
    <>
      <TypeDetailView type={q.data} onDelete={() => setDeleting(true)} />
      {deleting && (
        <TypeDeleteDialog
          type={q.data}
          onClose={() => setDeleting(false)}
          onDeleted={() => navigate({ to: "/types" })}
        />
      )}
    </>
  );
}

export const Route = createFileRoute("/types/$id/")({
  component: TypeDetailRoute,
});
