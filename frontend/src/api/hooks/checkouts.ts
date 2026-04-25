import { useQuery } from "@tanstack/react-query";
import { http } from "@/api/client";
import { qk } from "@/api/query-keys";
import { unwrap } from "@/lib/error";

export function useCheckoutHistoryQuery(assetId: string) {
  return useQuery({
    queryKey: qk.assets.history(assetId),
    queryFn: async () => {
      const res = await http.GET("/api/assets/{asset_id}/history", {
        params: { path: { asset_id: assetId } },
      });
      return unwrap(res);
    },
  });
}
