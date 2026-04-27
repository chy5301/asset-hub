import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { http } from "@/api/client";
import type { components } from "@/api/generated/schema";
import { qk } from "@/api/query-keys";
import { unwrap, unwrapVoid } from "@/lib/error";
import { uploadWithProgress } from "@/lib/upload-progress";

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
      unwrapVoid(res);
    },
    onSuccess: (_data, { assetId }) => {
      qc.invalidateQueries({ queryKey: qk.attachments.byAsset(assetId) });
      toast.success("附件已删除");
    },
    // 失败由调用方（AttachmentLightbox）通过 AlertDialog 内嵌提示展示。
  });
}

export function useUploadAttachmentMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (args: {
      assetId: string;
      file: File;
      onProgress?: (percent: number) => void;
    }) => {
      const fd = new FormData();
      fd.append("file", args.file);
      // 让后端默认 kind=OTHER；M2c-3 不让用户选 kind
      return await uploadWithProgress<components["schemas"]["AttachmentRead"]>(
        `/api/assets/${args.assetId}/attachments`,
        fd,
        args.onProgress,
      );
    },
    onSuccess: (_data, { assetId }) => {
      qc.invalidateQueries({ queryKey: qk.attachments.byAsset(assetId) });
    },
  });
}
