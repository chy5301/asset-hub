import { motion, useReducedMotion } from "motion/react";

import { ErrorState } from "@/components/feedback/error-state";
import { Route as DashboardRoute } from "@/routes/dashboard";

import { HolderLeaderboard } from "./charts/holder-leaderboard";
import { IdleTopBarChart } from "./charts/idle-top-bar-chart";
import { StatusDistributionChart } from "./charts/status-distribution-chart";
import { TypeDistributionChart } from "./charts/type-distribution-chart";
import { DashboardHeader } from "./dashboard-header";
import { DashboardSkeleton } from "./skeleton";
import { useStatsQuery } from "./use-stats-query";

export function DashboardPage() {
  const search = DashboardRoute.useSearch();
  const navigate = DashboardRoute.useNavigate();
  const statsQuery = useStatsQuery({
    includeRetired: search.include_retired,
    includeDisposed: search.include_disposed,
  });

  const reduceMotion = useReducedMotion();

  const transition = {
    duration: 0.32,
    ease: [0.16, 1, 0.3, 1] as const,
  };
  const idleInitial = reduceMotion ? { opacity: 0 } : { opacity: 0, x: -8 };
  const idleAnimate = reduceMotion ? { opacity: 1 } : { opacity: 1, x: 0 };
  const sideInitial = reduceMotion ? { opacity: 0 } : { opacity: 0, y: 8 };
  const sideAnimate = reduceMotion ? { opacity: 1 } : { opacity: 1, y: 0 };
  const STAGGER_DELAY = { type: 0.1, status: 0.18, holder: 0.26 } as const;

  return (
    <main className="relative min-h-[calc(100vh-4rem)] px-6 py-8 bg-background">
      <div className="border-b border-border/40 mb-8" />

      <DashboardHeader
        includeRetired={search.include_retired}
        includeDisposed={search.include_disposed}
        onToggle={(next) => navigate({ search: () => next })}
      />

      {statsQuery.isLoading ? (
        <DashboardSkeleton />
      ) : statsQuery.isError ? (
        <ErrorState error={statsQuery.error} onRetry={() => statsQuery.refetch()} />
      ) : statsQuery.data ? (
        <div className="grid grid-cols-12 gap-6 items-start">
          <motion.div
            data-motion-kind="idle"
            className="col-span-6"
            initial={idleInitial}
            animate={idleAnimate}
            transition={{ ...transition, delay: 0 }}
          >
            <IdleTopBarChart data={statsQuery.data.idle_top ?? []} />
          </motion.div>
          <div className="col-span-6 flex flex-col gap-6">
            <motion.div
              data-motion-kind="type"
              initial={sideInitial}
              animate={sideAnimate}
              transition={{ ...transition, delay: STAGGER_DELAY.type }}
            >
              <TypeDistributionChart data={statsQuery.data.type_distribution ?? []} />
            </motion.div>
            <motion.div
              data-motion-kind="status"
              initial={sideInitial}
              animate={sideAnimate}
              transition={{ ...transition, delay: STAGGER_DELAY.status }}
            >
              <StatusDistributionChart data={statsQuery.data.status_distribution ?? null} />
            </motion.div>
            <motion.div
              data-motion-kind="holder"
              initial={sideInitial}
              animate={sideAnimate}
              transition={{ ...transition, delay: STAGGER_DELAY.holder }}
            >
              <HolderLeaderboard data={statsQuery.data.holder_ranking ?? []} />
            </motion.div>
          </div>
        </div>
      ) : null}
    </main>
  );
}
