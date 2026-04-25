import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import type { components } from "@/api/generated/schema";
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

export function useCheckoutMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (args: {
      assetId: string;
      body: components["schemas"]["CheckoutCreate"];
    }) => {
      const res = await http.POST("/api/assets/{asset_id}/checkout", {
        params: { path: { asset_id: args.assetId } },
        body: args.body,
      });
      return unwrap(res);
    },
    onSuccess: (_data, { assetId }) => {
      qc.invalidateQueries({ queryKey: qk.assets.all });
      qc.invalidateQueries({ queryKey: qk.assets.detail(assetId) });
      qc.invalidateQueries({ queryKey: qk.assets.history(assetId) });
      toast.success("派发成功");
    },
    // 压制全局默认的 toast.error——Dialog 走 inline banner
    onError: () => {},
  });
}

export function useReturnMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (args: {
      assetId: string;
      body: components["schemas"]["CheckoutReturn"];
    }) => {
      const res = await http.POST("/api/assets/{asset_id}/return", {
        params: { path: { asset_id: args.assetId } },
        body: args.body,
      });
      return unwrap(res);
    },
    onSuccess: (_data, { assetId }) => {
      qc.invalidateQueries({ queryKey: qk.assets.all });
      qc.invalidateQueries({ queryKey: qk.assets.detail(assetId) });
      qc.invalidateQueries({ queryKey: qk.assets.history(assetId) });
      toast.success("归还成功");
    },
    onError: () => {},
  });
}
