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
    enabled: !!assetId, // 守护：列表页菜单未触发时 assetId="" 不发请求
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
      // qk.assets.history(id) = ["assets", id, "history"]，是 qk.assets.all 的子集，
      // 失效 ["assets"] 已自动级联失效 history。query-keys.ts §spec 5.1。
      qc.invalidateQueries({ queryKey: qk.assets.all });
      qc.invalidateQueries({ queryKey: qk.assets.detail(assetId) });
      toast.success("派发成功");
    },
    // 失败由调用方（CheckoutDialog）通过 inline banner 展示，不走全局 toast。
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
      toast.success("归还成功");
    },
  });
}
