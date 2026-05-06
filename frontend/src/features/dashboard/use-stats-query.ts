import { useQuery } from "@tanstack/react-query";

import { http } from "@/api/client";
import { qk } from "@/api/query-keys";
import { unwrap } from "@/api/types";
import type { StatsRead } from "@/features/assets/types";

interface UseStatsQueryParams {
  includeRetired: boolean;
  includeDisposed: boolean;
}

/**
 * GET /api/stats — 看板 4 段聚合 + summary.
 *
 * URL toggle (includeRetired / includeDisposed) 反映在 queryKey,
 * toggle 切换自动触发 refetch (React Query 的 query key 变化语义).
 *
 * staleTime 30s: 看板数据非实时, 短期缓存避免页面切换重复请求.
 */
export function useStatsQuery(params: UseStatsQueryParams) {
  return useQuery<StatsRead>({
    queryKey: qk.stats.detail(params),
    queryFn: async () => {
      const res = await http.GET("/api/stats", {
        params: {
          query: {
            include_retired: params.includeRetired,
            include_disposed: params.includeDisposed,
          },
        },
      });
      return unwrap(res);
    },
    staleTime: 30_000,
  });
}
