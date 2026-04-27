import { useEffect, useState } from "react";
import { Download, Trash2, X } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";
import { useDeleteAttachmentMutation } from "@/api/hooks/attachments";
import { toFriendlyMessage } from "@/lib/error";
import { formatDateTime } from "@/lib/date";
import { PENDING_TEXT } from "@/features/assets/form/form-toast";
import type { components } from "@/api/generated/schema";

type AttachmentRead = components["schemas"]["AttachmentRead"];

interface AttachmentLightboxProps {
  attachment: AttachmentRead | null;
  assetId: string;
  onClose: () => void;
}

export function AttachmentLightbox({
  attachment,
  assetId,
  onClose,
}: AttachmentLightboxProps) {
  const [confirmOpen, setConfirmOpen] = useState(false);
  const deleteMutation = useDeleteAttachmentMutation();
  const { reset: resetDelete } = deleteMutation;

  // 切换附件时把上一条 mutation 错误一并 reset（覆盖删除失败后切换到下一附件场景）
  useEffect(() => {
    resetDelete();
  }, [attachment?.id, resetDelete]);

  const open = attachment !== null;
  const deleteError = deleteMutation.error
    ? toFriendlyMessage(deleteMutation.error)
    : null;

  async function handleDelete() {
    if (!attachment) return;
    try {
      await deleteMutation.mutateAsync({
        attachmentId: attachment.id,
        assetId,
      });
      setConfirmOpen(false);
      onClose();
    } catch {
      // 错误展示由 deleteMutation.error 渲染；mutateAsync 仍需 catch 防 Unhandled promise rejection
    }
  }

  if (!attachment) return null;

  const contentUrl = `/api/attachments/${attachment.id}/content`;
  const isImage = attachment.mime_type.startsWith("image/");

  return (
    <>
      <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
        <DialogContent
          className="max-w-[90vw] max-h-[90vh] p-0 overflow-hidden"
        >
          <DialogTitle className="sr-only">{attachment.original_name}</DialogTitle>

          <div className="absolute right-2 top-2 z-10 flex gap-1">
            <Button
              variant="ghost"
              size="icon"
              aria-label="下载附件"
              onClick={() => window.open(contentUrl, "_blank")}
            >
              <Download className="h-4 w-4" />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              aria-label="删除附件"
              onClick={() => setConfirmOpen(true)}
            >
              <Trash2 className="h-4 w-4 text-destructive" />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              aria-label="关闭"
              onClick={onClose}
            >
              <X className="h-4 w-4" />
            </Button>
          </div>

          {isImage ? (
            <img
              src={contentUrl}
              alt={attachment.original_name}
              className="max-h-[90vh] w-auto object-contain"
            />
          ) : (
            <MetadataPanel att={attachment} contentUrl={contentUrl} />
          )}
        </DialogContent>
      </Dialog>

      <AlertDialog
        open={confirmOpen}
        onOpenChange={(v) => {
          setConfirmOpen(v);
          if (!v) deleteMutation.reset();
        }}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>确定删除附件？</AlertDialogTitle>
            <AlertDialogDescription>
              删除 <strong>{attachment.original_name}</strong> 后不可恢复。
            </AlertDialogDescription>
          </AlertDialogHeader>
          {deleteError && (
            <p className="text-sm text-destructive">{deleteError}</p>
          )}
          <AlertDialogFooter>
            <AlertDialogCancel disabled={deleteMutation.isPending}>
              取消
            </AlertDialogCancel>
            <AlertDialogAction
              onClick={(e) => {
                e.preventDefault();
                handleDelete();
              }}
              disabled={deleteMutation.isPending}
            >
              {deleteMutation.isPending ? PENDING_TEXT.DELETE : "确认删除"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}

function MetadataPanel({
  att,
  contentUrl,
}: {
  att: AttachmentRead;
  contentUrl: string;
}) {
  return (
    <div className="flex h-[50vh] flex-col items-center justify-center gap-4 p-10 text-center">
      <div className="space-y-2">
        <h3 className="text-lg font-medium">{att.original_name}</h3>
        <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 text-sm text-muted-foreground">
          <dt>类型</dt>
          <dd className="text-left font-code">{att.mime_type}</dd>
          <dt>大小</dt>
          <dd className="text-left font-code">
            {(att.size / 1024).toFixed(1)} KB
          </dd>
          <dt>上传时间</dt>
          <dd className="text-left font-code">{formatDateTime(att.uploaded_at)}</dd>
        </dl>
      </div>
      <Button onClick={() => window.open(contentUrl, "_blank")}>
        在新窗口打开
      </Button>
    </div>
  );
}
