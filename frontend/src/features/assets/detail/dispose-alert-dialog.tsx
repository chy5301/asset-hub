import { Trash2 } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import { useRecordTransitionMutation } from "@/api/hooks/transitions";
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
import { buttonVariants } from "@/components/ui/button";
import { InlineErrorBanner } from "@/components/feedback/inline-error-banner";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";
import { toFriendlyMessage } from "@/lib/error";

const CONFIRM_PHRASE = "处置";

interface DisposeAlertDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  assetId: string;
  assetName: string;
}

export function DisposeAlertDialog({
  open,
  onOpenChange,
  assetId,
  assetName,
}: DisposeAlertDialogProps) {
  const [confirmText, setConfirmText] = useState("");
  const [note, setNote] = useState("");
  const [rootError, setRootError] = useState<string | null>(null);
  const mutation = useRecordTransitionMutation(assetId);

  const unlocked = confirmText === CONFIRM_PHRASE;

  function handleOpenChange(v: boolean) {
    if (mutation.isPending) return;
    if (!v) {
      setConfirmText("");
      setNote("");
      setRootError(null);
    }
    onOpenChange(v);
  }

  async function onConfirm() {
    setRootError(null);
    try {
      await mutation.mutateAsync({
        kind: "DISPOSE",
        note: note.trim() || null,
      });
      toast.success("已处置");
      setConfirmText("");
      setNote("");
      onOpenChange(false);
    } catch (err) {
      setRootError(toFriendlyMessage(err));
    }
  }

  return (
    <AlertDialog open={open} onOpenChange={handleOpenChange}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <div className="flex items-center gap-2">
            <span className="inline-flex items-center gap-1.5 rounded-full bg-destructive/15 px-2.5 py-1 text-xs font-medium text-destructive">
              <Trash2 className="size-3.5" aria-hidden />
              处置
            </span>
          </div>
          <AlertDialogTitle>处置 {assetName}？</AlertDialogTitle>
          <AlertDialogDescription>
            <strong>此操作不可撤销</strong>
            。资产 holder 与 location 将被清空，状态置为已处置。
            如需确认，请在下方输入"{CONFIRM_PHRASE}"二字。
          </AlertDialogDescription>
        </AlertDialogHeader>

        {rootError && <InlineErrorBanner message={rootError} />}

        <div className="space-y-3">
          <Input
            value={confirmText}
            onChange={(e) => setConfirmText(e.target.value)}
            placeholder={`输入"${CONFIRM_PHRASE}"以解锁`}
            autoComplete="off"
            disabled={mutation.isPending}
          />
          <Textarea
            value={note}
            onChange={(e) => setNote(e.target.value)}
            placeholder="备注（可选，如卖给/捐赠/销毁原因）"
            disabled={mutation.isPending}
            rows={3}
          />
        </div>

        <AlertDialogFooter>
          <AlertDialogCancel disabled={mutation.isPending}>
            取消
          </AlertDialogCancel>
          <AlertDialogAction
            onClick={onConfirm}
            disabled={!unlocked || mutation.isPending}
            className={cn(buttonVariants({ variant: "destructive" }))}
          >
            {mutation.isPending ? "处置中…" : "确认处置"}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
