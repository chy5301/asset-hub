import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import type { ReactNode } from "react";
import { describe, expect, it } from "vitest";

import { useStatsQuery } from "@/features/dashboard/use-stats-query";

type MswServer = ReturnType<typeof setupServer>;
const server = (globalThis as unknown as { __mswServer: MswServer }).__mswServer;

const wrapper = ({ children }: { children: ReactNode }) => {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
};

describe("useStatsQuery", () => {
  it("fetches stats with toggle params reflected back", async () => {
    server.use(
      http.get("http://localhost:3000/api/stats", ({ request }) => {
        const url = new URL(request.url);
        return HttpResponse.json({
          type_distribution: [{ type_id: "uuid-1", type_name: "Laptop", count: 71 }],
          status_distribution: { IDLE: 78, IN_USE: 92, MAINTENANCE: 12 },
          holder_ranking: [{ holder: "张三", count: 28 }],
          idle_top: [],
          summary: {
            total_assets: 187,
            registered_assets: 182,
            idle_count: 78,
            include_retired: url.searchParams.get("include_retired") === "true",
            include_disposed: url.searchParams.get("include_disposed") === "true",
            generated_at: new Date().toISOString(),
          },
        });
      }),
    );
    const { result } = renderHook(
      () => useStatsQuery({ includeRetired: false, includeDisposed: false }),
      { wrapper },
    );
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.summary.include_retired).toBe(false);
    expect(result.current.data?.summary.include_disposed).toBe(false);
    expect(result.current.data?.type_distribution?.[0]?.type_name).toBe("Laptop");
  });

  it("toggle include_retired triggers refetch with new param", async () => {
    server.use(
      http.get("http://localhost:3000/api/stats", ({ request }) => {
        const url = new URL(request.url);
        const includeRetired = url.searchParams.get("include_retired") === "true";
        return HttpResponse.json({
          type_distribution: [{ type_id: "x", type_name: "L", count: 5 }],
          status_distribution: includeRetired
            ? { IDLE: 5, RETIRED: 4 }
            : { IDLE: 5 },
          holder_ranking: [],
          idle_top: [],
          summary: {
            total_assets: 5,
            registered_assets: 5,
            idle_count: 5,
            include_retired: includeRetired,
            include_disposed: false,
            generated_at: "2026-05-06T10:00:00Z",
          },
        });
      }),
    );
    const { result } = renderHook(
      () => useStatsQuery({ includeRetired: true, includeDisposed: false }),
      { wrapper },
    );
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.summary.include_retired).toBe(true);
    expect(result.current.data?.status_distribution).toHaveProperty("RETIRED");
  });
});
