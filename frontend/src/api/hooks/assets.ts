import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { http } from "@/api/client";
import { qk } from "@/api/query-keys";
import { unwrap } from "@/lib/error";
import type { components } from "@/api/generated/schema";
import type { AssetsSearch } from "@/features/assets/list/search-schema";

/** 只把后端接受的 filter 参数传过去；sort/page/pageSize 是客户端语义。 */
function toServerParams(search: AssetsSearch) {
  const params: Record<string, string> = {};
  if (search.type) params.type_id = search.type;
  if (search.status) params.status = search.status;
  if (search.holder) params.holder = search.holder;
  if (search.q) params.q = search.q;
  return params;
}

export function useAssetsQuery(search: AssetsSearch) {
  return useQuery({
    queryKey: qk.assets.list(search),
    queryFn: async () => {
      const res = await http.GET("/api/assets", {
        params: { query: toServerParams(search) },
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
  });
}

export function useDeleteAsset() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      const res = await http.DELETE("/api/assets/{asset_id}", {
        params: { path: { asset_id: id } },
      });
      return unwrap(res);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: qk.assets.all });
      toast.success("资产已删除");
    },
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
