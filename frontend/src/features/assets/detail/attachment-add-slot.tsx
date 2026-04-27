import { useRef, useState } from "react";
import { Plus, AlertCircle, RotateCw, X } from "lucide-react";
import { toast } from "sonner";
import { useUploadAttachmentMutation } from "@/api/hooks/attachments";
import { TOAST } from "@/features/assets/form/form-toast";
import { cn } from "@/lib/utils";

const MAX_SIZE_BYTES = 10 * 1024 * 1024; // 10MB

interface PendingFile {
  /** 临时本地 id（用于 React key） */
  localId: string;
  file: File;
  percent: number;
  error?: string;
}

interface AttachmentAddSlotProps {
  assetId: string;
}

export function AttachmentAddSlot({ assetId }: AttachmentAddSlotProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const localIdCounterRef = useRef(0);
  const [pending, setPending] = useState<PendingFile[]>([]);
  const [dragActive, setDragActive] = useState(false);
  const mutation = useUploadAttachmentMutation();

  function handleFiles(files: FileList | null) {
    if (!files || files.length === 0) return;
    const accepted: PendingFile[] = [];
    for (const file of Array.from(files)) {
      if (file.size > MAX_SIZE_BYTES) {
        toast.error(`${file.name}: ${TOAST.FILE_TOO_LARGE}`);
        continue;
      }
      localIdCounterRef.current += 1;
      accepted.push({
        localId: `pending-${localIdCounterRef.current}`,
        file,
        percent: 0,
      });
    }
    setPending((p) => [...p, ...accepted]);
    accepted.forEach((pf) => uploadOne(pf));
  }

  async function uploadOne(pf: PendingFile) {
    try {
      await mutation.mutateAsync({
        assetId,
        file: pf.file,
        onProgress: (percent) => {
          // XHR progress event 高频触发；percent 经 Math.round 后多次重复，避免 no-op re-render
          setPending((cur) => {
            const target = cur.find((p) => p.localId === pf.localId);
            if (!target || target.percent === percent) return cur;
            return cur.map((p) => (p.localId === pf.localId ? { ...p, percent } : p));
          });
        },
      });
      // 成功 → 从 pending 列表移除（attachment query 自动 invalidate 后会出现在 grid）
      setPending((cur) => cur.filter((p) => p.localId !== pf.localId));
      toast.success(TOAST.UPLOAD_SUCCESS);
    } catch (err: unknown) {
      const detail = (err as { detail?: string }).detail ?? "上传失败";
      setPending((cur) => cur.map((p) => (p.localId === pf.localId ? { ...p, error: detail } : p)));
    }
  }

  function retry(localId: string) {
    const pf = pending.find((p) => p.localId === localId);
    if (!pf) return;
    setPending((cur) =>
      cur.map((p) => (p.localId === localId ? { ...p, error: undefined, percent: 0 } : p)),
    );
    uploadOne(pf);
  }

  function dismiss(localId: string) {
    setPending((cur) => cur.filter((p) => p.localId !== localId));
  }

  return (
    <>
      {/* 上传中 / 失败 tile */}
      {pending.map((pf) => (
        <div
          key={pf.localId}
          className={cn(
            "aspect-square rounded-md ring-1 flex flex-col p-3",
            pf.error ? "ring-destructive bg-destructive/5" : "ring-border bg-muted/30",
          )}
        >
          <div className="flex justify-between gap-2">
            <span className="line-clamp-2 text-xs">{pf.file.name}</span>
            <button
              type="button"
              onClick={() => dismiss(pf.localId)}
              className="text-muted-foreground hover:text-foreground"
              aria-label="取消"
            >
              <X className="h-3 w-3" />
            </button>
          </div>
          <div className="mt-auto">
            {pf.error ? (
              <button
                type="button"
                onClick={() => retry(pf.localId)}
                className="flex items-center gap-1 text-xs text-destructive cursor-pointer"
                aria-label="重试上传"
              >
                <AlertCircle className="h-3 w-3" />
                <span>{pf.error}</span>
                <RotateCw className="ml-auto h-3 w-3" />
              </button>
            ) : (
              <>
                <div className="text-xs text-muted-foreground mb-1">{pf.percent}%</div>
                <div className="h-1 bg-secondary rounded">
                  <div
                    className="h-full bg-primary rounded transition-[width] duration-150 ease-out"
                    style={{ width: `${pf.percent}%` }}
                  />
                </div>
              </>
            )}
          </div>
        </div>
      ))}

      {/* add slot */}
      <button
        type="button"
        onClick={() => fileInputRef.current?.click()}
        onDragOver={(e) => {
          e.preventDefault();
          setDragActive(true);
        }}
        onDragLeave={() => setDragActive(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragActive(false);
          handleFiles(e.dataTransfer.files);
        }}
        className={cn(
          "aspect-square rounded-md border-[1.5px] border-dashed flex flex-col items-center justify-center gap-1 cursor-pointer transition-colors",
          dragActive
            ? "border-primary bg-primary/5 text-primary"
            : "border-muted-foreground/40 text-muted-foreground hover:border-primary hover:text-primary hover:bg-primary/5",
        )}
        aria-label="添加附件"
      >
        <Plus className="h-6 w-6" />
        <span className="text-xs">添加附件</span>
      </button>

      <input
        ref={fileInputRef}
        type="file"
        multiple
        className="hidden"
        accept="image/*,application/pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.txt,.md"
        onChange={(e) => {
          handleFiles(e.target.files);
          e.target.value = "";
        }}
      />
    </>
  );
}
