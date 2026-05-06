/**
 * Dashboard 加载 Skeleton (stub).
 *
 * Task 14 替换为 4 套形态匹配 Skeleton (idle 10 行 / donut / status bar / holder list).
 */
export function DashboardSkeleton() {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-[3fr_2fr] gap-6 min-h-[640px]">
      <div className="rounded-lg border bg-card p-6 animate-pulse" />
      <div className="grid grid-rows-3 gap-6">
        <div className="rounded-lg border bg-card p-6 animate-pulse" />
        <div className="rounded-lg border bg-card p-6 animate-pulse" />
        <div className="rounded-lg border bg-card p-6 animate-pulse" />
      </div>
    </div>
  );
}
