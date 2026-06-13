import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { http } from "@/api/client";
import type { components } from "@/api/generated/schema";
import { qk } from "@/api/query-keys";
import { unwrap } from "@/api/types";

type TransitionRead = components["schemas"]["TransitionRead"];
type TransitionCreate = components["schemas"]["TransitionCreate"];

export function useTransitionsQuery(assetId: string | undefined) {
  return useQuery({
    queryKey: assetId ? qk.assets.transitions(assetId) : ["disabled"],
    enabled: !!assetId,
    queryFn: async () => {
      const res = await http.GET("/api/assets/{asset_id}/transitions", {
        params: { path: { asset_id: assetId! } },
      });
      return unwrap(res);
    },
  });
}

export function useRecordTransitionMutation(assetId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: TransitionCreate): Promise<TransitionRead> => {
      const res = await http.POST("/api/assets/{asset_id}/transitions", {
        params: { path: { asset_id: assetId } },
        body,
      });
      return unwrap(res);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: qk.assets.detail(assetId) });
      qc.invalidateQueries({ queryKey: qk.assets.transitions(assetId) });
      qc.invalidateQueries({ queryKey: qk.assets.all });
    },
  });
}

export function useUndoLastTransitionMutation(assetId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (): Promise<TransitionRead> => {
      const res = await http.POST("/api/assets/{asset_id}/transitions/undo", {
        params: { path: { asset_id: assetId } },
      });
      return unwrap(res);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: qk.assets.detail(assetId) });
      qc.invalidateQueries({ queryKey: qk.assets.transitions(assetId) });
      qc.invalidateQueries({ queryKey: qk.assets.all });
    },
  });
}
