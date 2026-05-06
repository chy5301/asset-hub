/**
 * Dashboard 主页面 (D-原版): radial atmosphere + 顶部 hairline + grid 容器.
 *
 * spec §3.2: grid-cols-[3fr_2fr] 左 60% / 右 40%, 右列三段 stacked vertically.
 * 4 图组件 + Skeleton + ErrorBanner 当前为 stub, 由 Task 12-14 替换.
 */
import { Route as DashboardRoute } from "@/routes/dashboard";

import { HolderLeaderboard } from "./charts/holder-leaderboard";
import { IdleTopBarChart } from "./charts/idle-top-bar-chart";
import { StatusDistributionChart } from "./charts/status-distribution-chart";
import { TypeDistributionChart } from "./charts/type-distribution-chart";
import { DashboardHeader } from "./dashboard-header";
import { DashboardErrorBanner } from "./error-banner";
import { DashboardSkeleton } from "./skeleton";
import { useStatsQuery } from "./use-stats-query";

export function DashboardPage() {
  const search = DashboardRoute.useSearch();
  const navigate = DashboardRoute.useNavigate();
  const statsQuery = useStatsQuery({
    includeRetired: search.include_retired,
    includeDisposed: search.include_disposed,
  });

  return (
    <main
      className="relative min-h-[calc(100vh-4rem)] px-6 py-8"
      style={{
        backgroundImage:
          "radial-gradient(circle at 50% 20%, var(--dashboard-bg-radial-from), var(--dashboard-bg-radial-to))",
      }}
    >
      <div className="border-b border-border/40 mb-8" />

      <DashboardHeader
        includeRetired={search.include_retired}
        includeDisposed={search.include_disposed}
        onToggle={(next) => navigate({ search: () => next })}
      />

      {statsQuery.isLoading ? (
        <DashboardSkeleton />
      ) : statsQuery.isError ? (
        <DashboardErrorBanner onRetry={() => statsQuery.refetch()} />
      ) : statsQuery.data ? (
        <div className="grid grid-cols-1 lg:grid-cols-[3fr_2fr] gap-6 min-h-[640px]">
          <IdleTopBarChart data={statsQuery.data.idle_top ?? []} />
          <div className="grid grid-rows-3 gap-6">
            <TypeDistributionChart data={statsQuery.data.type_distribution ?? []} />
            <StatusDistributionChart data={statsQuery.data.status_distribution ?? null} />
            <HolderLeaderboard data={statsQuery.data.holder_ranking ?? []} />
          </div>
        </div>
      ) : null}
    </main>
  );
}
