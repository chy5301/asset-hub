import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { http } from "@/api/client";
import { qk } from "@/api/query-keys";
import { unwrap, unwrapVoid } from "@/api/types";
import type { components } from "@/api/generated/schema";

type TypeRead = components['schemas']['TypeRead'];
type TypeCreateBody = components['schemas']['TypeCreate'];
type TypeUpdateBody = components['schemas']['TypeUpdate'];

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
