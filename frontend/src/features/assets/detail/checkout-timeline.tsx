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

/**
 * 派发状态分桶。M2c-2 当前只有"组内派发"一种 kind；M3 §14.1 接入"向外出借"后，
 * 进行中的状态会自然分化为 "派发中" / "出借中"，已归还的卡通过 ring 边框色（蓝/琥珀）保留类型线索。
 * 此处单独抽函数为 M3 落地的修改面缩到一个点。
 */
function formatCheckoutStatus(c: CheckoutRead): { label: string; tone: "active" | "muted" } | null {
  // 已归还：不显示 pill，整卡 muted 调性表达"过去了"
  if (c.returned_at !== null) return null;
  // 进行中：M2c-2 只有 internal，固定显示"派发中"；M3 加 kind 后改 c.kind === 'external' ? '出借中' : '派发中'
  return { label: "派发中", tone: "active" };
}

function Card({ checkout: c }: { checkout: CheckoutRead }) {
  const ongoing = c.returned_at === null;
  const status = formatCheckoutStatus(c);
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
        {status ? (
          <span className="shrink-0 rounded-sm bg-[var(--status-active,#16a34a)]/10 px-2 py-0.5 text-xs font-medium text-[var(--status-active,#16a34a)]">
            {status.label}
          </span>
        ) : null}
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
