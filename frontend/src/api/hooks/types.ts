import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { http } from "@/api/client";
import { qk } from "@/api/query-keys";
import { useAssetsQuery } from "@/api/hooks/assets";
import { unwrap, unwrapVoid } from "@/lib/error";
import type { components } from "@/api/generated/schema";

type TypeRead = components['schemas']['TypeRead'];
type TypeCreateBody = components['schemas']['TypeCreate'];
type TypeUpdateBody = components['schemas']['TypeUpdate'];

// 临时 §Q workaround：TypeRead 缺 ref_count，前端反向数 assets。pageSize 统一为 200（zod schema ≥10），
// 上限隐患在 §Q 后端补字段后消除。任何 type→ref_count 计数路径走这个 hook，避免 callsite 间 pageSize 漂移。
const TYPE_REF_COUNT_PAGE_SIZE = 200;

export function useTypeRefCount(typeId: string) {
  const q = useAssetsQuery({
    type: typeId,
    page: 1,
    pageSize: TYPE_REF_COUNT_PAGE_SIZE,
    sort: 'asset_code',
  });
  return {
    count: q.data?.length ?? 0,
    isLoading: q.isLoading,
    isError: q.isError,
  };
}

export function useAssetTypesQuery() {
  return useQuery({
    queryKey: qk.assetTypes.list(),
    staleTime: Infinity, // 类型字典几乎不变
    queryFn: async () => {
      const res = await http.GET("/api/types");
      return unwrap(res);
    },
  });
}

export function useTypeQuery(id: string | undefined) {
  return useQuery({
    queryKey: qk.assetTypes.detail(id ?? ""),
    enabled: !!id,
    queryFn: async () => {
      const res = await http.GET("/api/types/{type_id}", {
        params: { path: { type_id: id! } },
      });
      return unwrap(res);
    },
  });
}

export function useCreateTypeMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: TypeCreateBody): Promise<TypeRead> => {
      const res = await http.POST("/api/types", { body });
      return unwrap(res);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: qk.assetTypes.all });
    },
  });
}

export function useUpdateTypeMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (args: { id: string; body: TypeUpdateBody }): Promise<TypeRead> => {
      const res = await http.PATCH("/api/types/{type_id}", {
        params: { path: { type_id: args.id } },
        body: args.body,
      });
      return unwrap(res);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: qk.assetTypes.all });
    },
  });
}

export function useDeleteTypeMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      const res = await http.DELETE("/api/types/{type_id}", {
        params: { path: { type_id: id } },
      });
      unwrapVoid(res);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: qk.assetTypes.all });
    },
  });
}
