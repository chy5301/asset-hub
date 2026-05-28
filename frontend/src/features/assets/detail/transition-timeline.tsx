import { useMemo } from "react";
import {
  AlertTriangle,
  ArrowRightFromLine,
  ArchiveRestore,
  Clock,
  Moon,
  PackageCheck,
  ShieldCheck, ShieldOff, Shuffle,
  Trash2, Undo2, Wrench,
  type LucideIcon,
} from "lucide-react";
import type { UseQueryResult } from "@tanstack/react-query";

import type { AssetStatus, TransitionKind, TransitionRead } from "@/features/assets/types";
import { useTransitionsQuery } from "@/api/hooks/transitions";
import { EmptyState } from "@/components/feedback/empty-state";
import { ErrorState } from "@/components/feedback/error-state";
import { Skeleton } from "@/components/ui/skeleton";
import {
  groupByMonth,
  groupByCheckout,
  type GroupedTransition,
} from "@/lib/timeline-grouping";
import { calcOverdue } from "@/lib/overdue";
import { formatDate, formatRelative } from "@/lib/date";
import { cn } from "@/lib/utils";

interface KindMeta {
  label: string;
  Icon: LucideIcon;
  bgClass: string;
  fgClass: string;
}

/** 静态 class map：Tailwind 不能动态拼接，必须每个 kind 显式写出 utility 字符串。
 *  与 status-badge.tsx 视觉惯例一致；/15 alpha modifier 让 chip 视觉更轻。 */
const KIND_META: Record<TransitionKind, KindMeta> = {
  CHECKOUT_INTERNAL:        { label: "派发",       Icon: ArrowRightFromLine, bgClass: "bg-status-in-use/15",      fgClass: "text-status-in-use-fg" },
  CHECKOUT_EXTERNAL:        { label: "出借",       Icon: ArrowRightFromLine, bgClass: "bg-status-borrowed/15",    fgClass: "text-status-borrowed-fg" },
  RETURN:                   { label: "归还",       Icon: Undo2,              bgClass: "bg-status-idle/15",        fgClass: "text-status-idle-fg" },
  SEND_TO_MAINTENANCE:      { label: "送修",       Icon: Wrench,             bgClass: "bg-status-maintenance/15", fgClass: "text-status-maintenance-fg" },
  RECOVER_FROM_MAINTENANCE: { label: "维修完成",   Icon: PackageCheck,       bgClass: "bg-status-idle/15",        fgClass: "text-status-idle-fg" },
  RETIRE:                   { label: "退役",       Icon: Moon,               bgClass: "bg-status-retired/15",     fgClass: "text-status-retired-fg" },
  REINSTATE:                { label: "重新启用",   Icon: ArchiveRestore,     bgClass: "bg-status-idle/15",        fgClass: "text-status-idle-fg" },
  DISPOSE:                  { label: "注销",       Icon: Trash2,             bgClass: "bg-status-disposed/15",    fgClass: "text-status-disposed-fg" },
  REASSIGN:                 { label: "重新分配",   Icon: Shuffle,            bgClass: "bg-muted",                 fgClass: "text-muted-foreground" },
  REPORT_BROKEN:            { label: "出现故障",   Icon: AlertTriangle,      bgClass: "bg-status-broken/15",      fgClass: "text-status-broken-fg" },
  DECLARE_UNREPAIRABLE:     { label: "故障报废",   Icon: ShieldOff,          bgClass: "bg-status-broken/15",      fgClass: "text-status-broken-fg" },
  DISMISS:                  { label: "故障解除",   Icon: ShieldCheck,        bgClass: "bg-status-idle/15",        fgClass: "text-status-idle-fg" },
};

function formatLine(t: TransitionRead): string {
  switch (t.kind) {
    case "CHECKOUT_INTERNAL":
      return `派发给 ${t.to_holder}` + (t.to_location ? ` · 位置 ${t.to_location}` : "");
    case "CHECKOUT_EXTERNAL":
      return `出借给 ${t.to_holder}` + (t.to_location ? ` · 位置 ${t.to_location}` : "");
    case "RETURN":
      return `归还给 ${t.to_holder ?? "无人值守"}`;
    case "SEND_TO_MAINTENANCE":
      return "送修";
    case "RECOVER_FROM_MAINTENANCE":
      return "维修完成";
    case "RETIRE":
      return "退役";
    case "REINSTATE":
      return "重新启用";
    case "DISPOSE":
      return "注销";
    case "REASSIGN": {
      const parts: string[] = [];
      if (t.from_holder !== t.to_holder) {
        parts.push(`持有人 ${t.from_holder ?? "(空)"} → ${t.to_holder ?? "(空)"}`);
      }
      if (t.from_location !== t.to_location) {
        parts.push(`位置 ${t.from_location ?? "(空)"} → ${t.to_location ?? "(空)"}`);
      }
      return parts.join(" · ") || "重新分配";
    }
    case "REPORT_BROKEN":
      return "出现故障" + (t.note ? ` · ${t.note}` : "");
    case "DECLARE_UNREPAIRABLE":
      return "故障报废" + (t.note ? ` · ${t.note}` : "");
    case "DISMISS":
      return "故障解除" + (t.note ? ` · ${t.note}` : "");
  }
}

interface TransitionTimelineProps {
  assetId: string;
  assetStatus: AssetStatus;
}

export function TransitionTimeline({ assetId, assetStatus }: TransitionTimelineProps) {
  const query: UseQueryResult<TransitionRead[]> = useTransitionsQuery(assetId);

  const grouped = useMemo<GroupedTransition[]>(
    () => (query.data ? groupByCheckout(query.data) : []),
    [query.data],
  );
  const months = useMemo(() => groupByMonth(grouped), [grouped]);

  return (
    <section>
      <h2 className="mb-3 text-lg font-medium">流转记录</h2>
      {query.isLoading ? (
        <TimelineSkeleton />
      ) : query.isError ? (
        <ErrorState error={query.error} onRetry={() => query.refetch()} />
      ) : (query.data ?? []).length === 0 ? (
        <EmptyState title="暂无流转记录" description="发生 transition 后会在此出现记录。" />
      ) : (
        months.map(({ month, items }) => (
          <div key={month} className="mb-3">
            <h3 className="sticky top-0 bg-background pb-1.5 pt-3 text-xs uppercase tracking-wide text-muted-foreground border-b border-border/40 font-medium first:pt-0 z-10">
              {month}
            </h3>
            <ol className="space-y-3 mt-2">
              {items.map((t) => (
                <TransitionCard key={t.id} t={t} assetStatus={assetStatus} />
              ))}
            </ol>
          </div>
        ))
      )}
    </section>
  );
}

function TransitionCard({
  t,
  assetStatus,
}: {
  t: GroupedTransition;
  assetStatus: AssetStatus;
}) {
  const meta = KIND_META[t.kind];
  const Icon = meta.Icon;
  const group = t.group;

  // 仅 OPEN CHECKOUT 卡：kind 是 CHECKOUT_*，position 是 start，且 asset 仍 IN_USE
  const isOpenCheckout =
    (t.kind === "CHECKOUT_INTERNAL" || t.kind === "CHECKOUT_EXTERNAL") &&
    group?.position === "start" &&
    assetStatus === "IN_USE";
  const overdue = isOpenCheckout ? calcOverdue(t.due_at, assetStatus) : null;

  return (
    <li className="rounded-lg ring-1 ring-border/60 p-3 flex items-start gap-3 relative">
      {/* Group rail 单 span：start/middle 用 -bottom-3 跨 space-y-3 gap，end 在 li 内收束。
       *  -z-10 让 rail 躲到 chip / time 等内容下方，避免半像素重叠成视觉脏点。 */}
      {group && (
        <span
          className={cn(
            "absolute left-0 w-0.5 -z-10",
            group.position === "start" && "top-1.5 -bottom-3",
            group.position === "middle" && "top-0 -bottom-3",
            group.position === "end" && "top-0 bottom-1.5",
            group.kind === "in-use" && "bg-status-in-use/40",
            group.kind === "external" && "bg-status-borrowed/40",
          )}
          aria-hidden
        />
      )}

      <span
        className={cn(
          "inline-flex items-center justify-center size-8 rounded-full shrink-0",
          meta.bgClass,
          meta.fgClass,
        )}
      >
        <Icon className="size-4" aria-hidden />
      </span>

      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium">{formatLine(t)}</p>
        {t.note && <p className="text-xs text-muted-foreground mt-1">{t.note}</p>}

        {/* 超期提示行（仅 OPEN CHECKOUT）*/}
        {overdue && overdue.status !== "pending" && (
          <p
            className={cn(
              "text-xs font-medium mt-1 inline-flex items-center gap-1",
              overdue.status === "due-soon" && "text-warning-fg",
              overdue.status === "overdue" && "text-destructive",
            )}
          >
            <Clock className="size-3" aria-hidden />
            {overdue.status === "due-soon" ? `还有 ${overdue.days} 天到期` : `逾期 ${overdue.days} 天`}
          </p>
        )}
      </div>

      <time className="text-xs text-muted-foreground font-code shrink-0">
        {formatDate(t.created_at)} · {formatRelative(t.created_at)}
      </time>
    </li>
  );
}

/** 内嵌 skeleton（沿用旧 checkout-timeline.tsx 的 inline 形态，不抽到 feedback/）。 */
function TimelineSkeleton() {
  return (
    <ol className="space-y-3">
      {Array.from({ length: 3 }).map((_, i) => (
        <li
          key={i}
          className="rounded-lg ring-1 ring-border/60 p-3 flex items-start gap-3"
        >
          <Skeleton className="size-8 rounded-full shrink-0" />
          <div className="flex-1 space-y-2">
            <Skeleton className="h-4 w-32" />
            <Skeleton className="h-3 w-48" />
          </div>
          <Skeleton className="h-3 w-24 shrink-0" />
        </li>
      ))}
    </ol>
  );
}
