import { useEffect, useRef, useState } from "react";
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
import type { AttachmentRead } from "@/features/assets/types";

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
          className="!max-w-[90vw] max-h-[90vh] p-0 overflow-hidden"
          showCloseButton={false}
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
            <ZoomableImage src={contentUrl} alt={attachment.original_name} key={attachment.id} />
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

const MIN_SCALE = 0.25;
const MAX_SCALE = 8;

function ZoomableImage({ src, alt }: { src: string; alt: string }) {
  const [scale, setScale] = useState(1);
  const [tx, setTx] = useState(0);
  const [ty, setTy] = useState(0);
  const [dragging, setDragging] = useState(false);
  const dragRef = useRef<{ x: number; y: number; tx: number; ty: number } | null>(null);
  const containerRef = useRef<HTMLDivElement | null>(null);

  function handleWheel(e: React.WheelEvent<HTMLDivElement>) {
    e.preventDefault();
    const rect = containerRef.current?.getBoundingClientRect();
    if (!rect) return;
    const cx = e.clientX - rect.left - rect.width / 2;
    const cy = e.clientY - rect.top - rect.height / 2;
    const factor = e.deltaY < 0 ? 1.1 : 1 / 1.1;
    const next = Math.min(MAX_SCALE, Math.max(MIN_SCALE, scale * factor));
    if (next === scale) return;
    // 围绕鼠标位置缩放：保持 (cx,cy) 在世界坐标中不变
    const ratio = next / scale;
    setTx((prev) => cx - (cx - prev) * ratio);
    setTy((prev) => cy - (cy - prev) * ratio);
    setScale(next);
  }

  function handleDoubleClick() {
    setScale(1);
    setTx(0);
    setTy(0);
  }

  function handlePointerDown(e: React.PointerEvent<HTMLDivElement>) {
    if (scale === 1) return;
    (e.target as HTMLElement).setPointerCapture(e.pointerId);
    dragRef.current = { x: e.clientX, y: e.clientY, tx, ty };
    setDragging(true);
  }

  function handlePointerMove(e: React.PointerEvent<HTMLDivElement>) {
    if (!dragRef.current) return;
    setTx(dragRef.current.tx + (e.clientX - dragRef.current.x));
    setTy(dragRef.current.ty + (e.clientY - dragRef.current.y));
  }

  function handlePointerUp() {
    dragRef.current = null;
    setDragging(false);
  }

  return (
    <div
      ref={containerRef}
      className="relative flex h-[90vh] w-full items-center justify-center overflow-hidden bg-black/5 select-none"
      onWheel={handleWheel}
      onDoubleClick={handleDoubleClick}
      onPointerDown={handlePointerDown}
      onPointerMove={handlePointerMove}
      onPointerUp={handlePointerUp}
      onPointerCancel={handlePointerUp}
      style={{ cursor: scale > 1 ? (dragging ? "grabbing" : "grab") : "zoom-in" }}
      aria-label="可缩放图片：滚轮缩放，双击重置，缩放后可拖拽"
    >
      <img
        src={src}
        alt={alt}
        draggable={false}
        className="max-h-[90vh] w-auto object-contain pointer-events-none"
        style={{ transform: `translate(${tx}px, ${ty}px) scale(${scale})`, transformOrigin: "center center" }}
      />
      <div className="absolute bottom-2 right-2 rounded bg-black/60 px-2 py-0.5 font-code text-xs text-white">
        {Math.round(scale * 100)}%
      </div>
    </div>
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
