// frontend/src/features/assets/detail/checkout-timeline.tsx
import { format, parseISO } from "date-fns";
import { EmptyState } from "@/components/feedback/empty-state";
import { ErrorState } from "@/components/feedback/error-state";
import { Skeleton } from "@/components/ui/skeleton";
import type { components } from "@/api/generated/schema";
import type { UseQueryResult } from "@tanstack/react-query";

type CheckoutRead = components["schemas"]["CheckoutRead"];

interface CheckoutTimelineProps {
  query: UseQueryResult<CheckoutRead[]>;
}

export function CheckoutTimeline({ query }: CheckoutTimelineProps) {
  return (
    <section>
      <h2 className="mb-3 text-lg font-medium">流转记录</h2>
      {query.isLoading ? (
        <TimelineSkeleton />
      ) : query.isError ? (
        <ErrorState error={query.error} onRetry={() => query.refetch()} />
      ) : (query.data ?? []).length === 0 ? (
        <EmptyState title="暂无流转记录" description="派发后会在此出现记录。" />
      ) : (
        <ol className="relative pl-6">
          <div
            aria-hidden
            className="absolute left-[7px] top-2 bottom-2 w-px bg-border"
          />
          {(query.data ?? []).map((c) => (
            <li key={c.id} className="relative pb-6 last:pb-0">
              <Node isCurrent={c.returned_at === null} />
              <Card checkout={c} />
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}

function Node({ isCurrent }: { isCurrent: boolean }) {
  return (
    <span
      aria-hidden
      className={
        isCurrent
          ? "absolute left-0 top-1.5 block h-4 w-4 rounded-full bg-[var(--status-active,#16a34a)]"
          : "absolute left-0.5 top-2 block h-3 w-3 rounded-full border-2 border-muted-foreground bg-background"
      }
    />
  );
}

function Card({ checkout: c }: { checkout: CheckoutRead }) {
  const ongoing = c.returned_at === null;
  return (
    <div className="rounded-md ring-1 ring-border/60 p-3 space-y-1">
      <div className="flex items-center justify-between">
        <p className="font-medium">
          {c.holder}
          {c.location ? (
            <span className="ml-2 text-sm text-muted-foreground">
              @ {c.location}
            </span>
          ) : null}
        </p>
        {ongoing && (
          <span className="rounded-sm bg-[var(--status-active,#16a34a)]/10 px-2 py-0.5 text-xs font-medium text-[var(--status-active,#16a34a)]">
            进行中
          </span>
        )}
      </div>
      <p className="font-code text-sm text-muted-foreground">
        {format(parseISO(c.checked_out_at), "yyyy-MM-dd HH:mm")}{" "}
        {ongoing ? (
          <span className="text-muted-foreground">→ —</span>
        ) : (
          <>→ {format(parseISO(c.returned_at!), "yyyy-MM-dd HH:mm")}</>
        )}
      </p>
      {c.checkout_note ? (
        <p className="text-sm text-muted-foreground">
          派发备注：{c.checkout_note}
        </p>
      ) : null}
      {c.return_note && !ongoing ? (
        <p className="text-sm text-muted-foreground">
          归还备注：{c.return_note}
        </p>
      ) : null}
    </div>
  );
}

function TimelineSkeleton() {
  return (
    <div className="relative pl-6 space-y-4">
      {Array.from({ length: 3 }).map((_, i) => (
        <div key={i} className="flex gap-4">
          <Skeleton className="h-3 w-3 rounded-full" />
          <div className="flex-1 space-y-2">
            <Skeleton className="h-4 w-40" />
            <Skeleton className="h-3 w-48" />
          </div>
        </div>
      ))}
    </div>
  );
}
