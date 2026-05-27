import { Link, useNavigate } from "@tanstack/react-router";

import { useTypeQuery } from "@/api/hooks/types";
import { ErrorState } from "@/components/feedback/error-state";
import { Skeleton } from "@/components/ui/skeleton";
import { isHttpError } from "@/lib/error";
import { TypeForm } from "../form/type-form";
import { TypeNotFound } from "./type-not-found";

export function TypeEditPage({ id }: { id: string }) {
  const navigate = useNavigate();
  const q = useTypeQuery(id);

  if (q.isLoading) return <Skeleton className="h-96 w-full" />;
  if (q.isError) {
    const is404 = isHttpError(q.error) && q.error.status === 404;
    if (is404) return <TypeNotFound />;
    return <ErrorState error={q.error} onRetry={() => q.refetch()} />;
  }
  if (!q.data) return null;

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <Link
        to="/types/$id"
        params={{ id }}
        className="text-sm text-muted-foreground hover:text-foreground transition-colors"
      >
        ← 返回类型详情
      </Link>
      <h1 className="text-2xl font-semibold">编辑类型 · {q.data.name}</h1>
      <TypeForm
        mode="edit"
        initial={q.data}
        onSuccess={() => navigate({ to: "/types/$id", params: { id } })}
      />
    </div>
  );
}
