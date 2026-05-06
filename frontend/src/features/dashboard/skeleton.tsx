/**
 * Dashboard 加载 Skeleton — 4 套形态匹配 (spec §3.8).
 *
 * - IdleTopSkeleton: 10 行不同长度 bar pulse
 * - DonutSkeleton: 圆环 outline + 3 行 legend pulse
 * - StatusBarSkeleton: 1 条 bar + 5 dot pulse
 * - HolderListSkeleton: 5 行 avatar + name + chip pulse
 *
 * 内部辅助组件不 export, 仅暴露 DashboardSkeleton.
 */

const IDLE_BAR_WIDTHS = [90, 82, 70, 58, 45, 32, 28, 22, 18, 12]; // %
const DONUT_LEGEND_WIDTHS = ["w-3/4", "w-2/3", "w-1/2"];
const STATUS_DOT_COUNT = 5;
const HOLDER_ROW_COUNT = 5;

export function DashboardSkeleton() {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-[3fr_2fr] gap-6 min-h-[640px]">
      <IdleTopSkeleton />
      <div className="grid grid-rows-3 gap-6">
        <DonutSkeleton />
        <StatusBarSkeleton />
        <HolderListSkeleton />
      </div>
    </div>
  );
}

function IdleTopSkeleton() {
  return (
    <div className="rounded-lg border bg-card p-6">
      <div className="h-4 w-32 bg-muted/40 rounded mb-6 animate-pulse" />
      <ul className="space-y-2">
        {IDLE_BAR_WIDTHS.map((w, i) => (
          <li key={i} className="grid grid-cols-[1fr_auto_auto] items-center gap-3">
            <div className="h-3 w-24 bg-muted/40 rounded animate-pulse" />
            <div className="w-32 sm:w-48 h-2 bg-muted/40 rounded-full overflow-hidden">
              <div
                className="h-full bg-muted/60 rounded-full animate-pulse"
                style={{ width: `${w}%` }}
              />
            </div>
            <div className="h-3 w-10 bg-muted/40 rounded animate-pulse" />
          </li>
        ))}
      </ul>
    </div>
  );
}

function DonutSkeleton() {
  return (
    <div className="rounded-lg border bg-card p-6 flex items-center gap-6">
      <div className="size-32 rounded-full border-[10px] border-muted/40 animate-pulse" />
      <div className="flex-1 space-y-2">
        {DONUT_LEGEND_WIDTHS.map((w) => (
          <div key={w} className={`h-3 ${w} bg-muted/40 rounded animate-pulse`} />
        ))}
      </div>
    </div>
  );
}

function StatusBarSkeleton() {
  return (
    <div className="rounded-lg border bg-card p-6">
      <div className="h-4 w-24 bg-muted/40 rounded mb-4 animate-pulse" />
      <div className="h-9 w-full bg-muted/40 rounded-md animate-pulse" />
      <div className="flex gap-3 mt-3">
        {Array.from({ length: STATUS_DOT_COUNT }).map((_, i) => (
          <div key={i} className="h-3 w-12 bg-muted/40 rounded animate-pulse" />
        ))}
      </div>
    </div>
  );
}

function HolderListSkeleton() {
  return (
    <div className="rounded-lg border bg-card p-6">
      <div className="h-4 w-28 bg-muted/40 rounded mb-4 animate-pulse" />
      <ul className="space-y-2">
        {Array.from({ length: HOLDER_ROW_COUNT }).map((_, i) => (
          <li key={i} className="grid grid-cols-[auto_1fr_auto] items-center gap-2 py-1.5">
            <div className="size-5 rounded-full bg-muted/40 animate-pulse" />
            <div className="h-3 bg-muted/40 rounded animate-pulse" />
            <div className="h-3 w-8 bg-muted/40 rounded animate-pulse" />
          </li>
        ))}
      </ul>
    </div>
  );
}
