import {
  ArrowRightFromLine, CheckCircle2, MapPin, Moon, Send,
  Sun, Trash2, Undo2, UserCog, Wrench, type LucideIcon,
} from "lucide-react";
import type { UseQueryResult } from "@tanstack/react-query";

import type { components } from "@/api/generated/schema";
import { useTransitionsQuery } from "@/api/hooks/transitions";
import { EmptyState } from "@/components/feedback/empty-state";
import { ErrorState } from "@/components/feedback/error-state";
import { Skeleton } from "@/components/ui/skeleton";
import { formatDateTime } from "@/lib/date";

type TransitionKind = components["schemas"]["TransitionKind"];
type TransitionRead = components["schemas"]["TransitionRead"];

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
  CHECKOUT_EXTERNAL:        { label: "出借",       Icon: Send,               bgClass: "bg-status-in-use/15",      fgClass: "text-status-in-use-fg" },
  RETURN:                   { label: "归还",       Icon: Undo2,              bgClass: "bg-status-idle/15",        fgClass: "text-status-idle-fg" },
  SEND_TO_MAINTENANCE:      { label: "送修",       Icon: Wrench,             bgClass: "bg-status-maintenance/15", fgClass: "text-status-maintenance-fg" },
  RECOVER_FROM_MAINTENANCE: { label: "维修完成",   Icon: CheckCircle2,       bgClass: "bg-status-idle/15",        fgClass: "text-status-idle-fg" },
  RETIRE:                   { label: "退役",       Icon: Moon,               bgClass: "bg-status-retired/15",     fgClass: "text-status-retired-fg" },
  REINSTATE:                { label: "重新启用",   Icon: Sun,                bgClass: "bg-status-idle/15",        fgClass: "text-status-idle-fg" },
  DISPOSE:                  { label: "处置",       Icon: Trash2,             bgClass: "bg-status-disposed/15",    fgClass: "text-status-disposed-fg" },
  RELOCATE:                 { label: "变更位置",   Icon: MapPin,             bgClass: "bg-muted",                 fgClass: "text-muted-foreground" },
  TRANSFER_HOLDER:          { label: "变更保管人", Icon: UserCog,            bgClass: "bg-muted",                 fgClass: "text-muted-foreground" },
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
      return "处置";
    case "RELOCATE":
      return `变更位置至 ${t.to_location}`;
    case "TRANSFER_HOLDER":
      return `变更保管人 ${t.from_holder ?? "无"} → ${t.to_holder}`;
  }
}

interface TransitionTimelineProps {
  assetId: string;
}

export function TransitionTimeline({ assetId }: TransitionTimelineProps) {
  const query: UseQueryResult<TransitionRead[]> = useTransitionsQuery(assetId);

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
        <ol className="space-y-3">
          {(query.data ?? []).map((t) => {
            const meta = KIND_META[t.kind];
            const Icon = meta.Icon;
            return (
              <li
                key={t.id}
                className="rounded-lg ring-1 ring-border/60 p-3 flex items-start gap-3"
              >
                <span
                  className={`inline-flex items-center justify-center size-8 rounded-full shrink-0 ${meta.bgClass} ${meta.fgClass}`}
                >
                  <Icon className="size-4" aria-hidden />
                </span>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium">{formatLine(t)}</p>
                  {t.note && (
                    <p className="text-xs text-muted-foreground mt-1">{t.note}</p>
                  )}
                </div>
                <time className="text-xs text-muted-foreground font-code shrink-0">
                  {formatDateTime(t.created_at)}
                </time>
              </li>
            );
          })}
        </ol>
      )}
    </section>
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
