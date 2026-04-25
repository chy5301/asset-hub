import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { http } from "@/api/client";
import { qk } from "@/api/query-keys";
import { unwrap } from "@/lib/error";

export function useAttachmentsQuery(assetId: string) {
  return useQuery({
    queryKey: qk.attachments.byAsset(assetId),
    queryFn: async () => {
      const res = await http.GET("/api/assets/{asset_id}/attachments", {
        params: { path: { asset_id: assetId } },
      });
      return unwrap(res);
    },
  });
}

export function useDeleteAttachmentMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (args: { attachmentId: string; assetId: string }) => {
      const res = await http.DELETE("/api/attachments/{attachment_id}", {
        params: { path: { attachment_id: args.attachmentId } },
      });
      // 204 返回无 body，openapi-fetch 会给 data=undefined。这里不能用 unwrap（unwrap 要求 data 存在）
      if (res.error) {
        const detail =
          typeof res.error === "object" && res.error !== null
            ? (res.error as { detail?: string }).detail
            : undefined;
        throw { status: res.response.status, detail };
      }
      // 成功返回，无 body
    },
    onSuccess: (_data, { assetId }) => {
      qc.invalidateQueries({ queryKey: qk.attachments.byAsset(assetId) });
      toast.success("附件已删除");
    },
    onError: () => {},
  });
}
