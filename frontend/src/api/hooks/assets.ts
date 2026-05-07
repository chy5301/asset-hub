import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { http } from "@/api/client";
import { qk } from "@/api/query-keys";
import { toFriendlyMessage } from "@/lib/error";
import { unwrap } from "@/api/types";
import type { components } from "@/api/generated/schema";
import { searchToServerParams } from "@/features/assets/list/search-params";
import type { AssetsSearch } from "@/features/assets/list/search-schema";

export function useAssetsQuery(search: AssetsSearch) {
  return useQuery({
    queryKey: qk.assets.list(search),
    queryFn: async () => {
      const res = await http.GET("/api/assets", {
        params: { query: searchToServerParams(search) },
      });
      return unwrap(res);
    },
  });
}

export function useCreateAsset() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: components["schemas"]["AssetCreate"]) => {
      const res = await http.POST("/api/assets", { body });
      return unwrap(res);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: qk.assets.all });
      toast.success("资产已登记");
    },
    onError: (err) => toast.error(toFriendlyMessage(err)),
  });
}

export function useUpdateAsset(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: components["schemas"]["AssetUpdate"]) => {
      const res = await http.PATCH("/api/assets/{asset_id}", {
        params: { path: { asset_id: id } },
        body,
      });
      return unwrap(res);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: qk.assets.all });
      toast.success("资产已更新");
    },
    onError: (err) => toast.error(toFriendlyMessage(err)),
  });
}

export function useDeleteAsset() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      const res = await http.DELETE("/api/assets/{asset_id}", {
        params: { path: { asset_id: id } },
      });
      // DELETE 返回 204，没有 data；不能用 unwrap（会抛 missing data）
      if (res.error) throw res.error;
      return undefined;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: qk.assets.all });
    },
    // toast 由调用方控制（DeleteAssetAlert）
  });
}

export function useAssetDetailQuery(id: string) {
  return useQuery({
    queryKey: qk.assets.detail(id),
    queryFn: async () => {
      const res = await http.GET("/api/assets/{asset_id}", {
        params: { path: { asset_id: id } },
      });
      return unwrap(res);
    },
    // 404 靠 errorComponent / isError 分支处理，不在此重试
  });
}
