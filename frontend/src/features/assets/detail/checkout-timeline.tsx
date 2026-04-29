import { EmptyState } from "@/components/feedback/empty-state";
import { ErrorState } from "@/components/feedback/error-state";
import { Skeleton } from "@/components/ui/skeleton";
import { formatDateTime } from "@/lib/date";
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
        <ol className="space-y-3">
          {(query.data ?? []).map((c) => (
            <li key={c.id}>
              <Card checkout={c} />
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}

function Card({ checkout: c }: { checkout: CheckoutRead }) {
  const ongoing = c.returned_at === null;
  return (
    <div
      className={
        ongoing
          ? "rounded-md ring-1 ring-border/60 p-3 space-y-1"
          : "rounded-md ring-1 ring-border/40 p-3 space-y-1 text-muted-foreground"
      }
    >
      <div className="flex items-start justify-between gap-3">
        <p className={ongoing ? "font-medium" : "font-medium text-foreground/80"}>
          {c.holder}
          {c.location ? (
            <span className="ml-2 text-sm text-muted-foreground">
              @ {c.location}
            </span>
          ) : null}
        </p>
        {ongoing && (
          <span className="shrink-0 rounded-sm bg-[var(--status-active,#16a34a)]/10 px-2 py-0.5 text-xs font-medium text-[var(--status-active,#16a34a)]">
            派发中
          </span>
        )}
      </div>
      <p className="font-code text-sm text-muted-foreground">
        {formatDateTime(c.checked_out_at)}{" "}
        {ongoing ? (
          <span className="text-muted-foreground">→ —</span>
        ) : (
          <>→ {formatDateTime(c.returned_at!)}</>
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
      {c.return_location && !ongoing ? (
        <p className="text-sm text-muted-foreground">
          归还至：{c.return_location}
        </p>
      ) : null}
      {c.return_receiver && !ongoing ? (
        <p className="text-sm text-muted-foreground">
          接收人：{c.return_receiver}
        </p>
      ) : null}
    </div>
  );
}

function TimelineSkeleton() {
  return (
    <div className="space-y-3">
      {Array.from({ length: 3 }).map((_, i) => (
        <Skeleton key={i} className="h-20 w-full rounded-md" />
      ))}
    </div>
  );
}
