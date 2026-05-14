import { useState } from "react";
import { ShieldOff } from "lucide-react";
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
import { InlineErrorBanner } from "@/components/feedback/inline-error-banner";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { toFriendlyMessage } from "@/lib/error";

interface DeclareUnrepairableAlertDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  assetId: string;
  assetName: string;
}

export function DeclareUnrepairableAlertDialog({
  open,
  onOpenChange,
  assetId,
  assetName,
}: DeclareUnrepairableAlertDialogProps) {
  const [note, setNote] = useState("");
  const [error, setError] = useState<string | null>(null);
  const mutation = useRecordTransitionMutation(assetId);

  function handleOpenChange(v: boolean) {
    if (mutation.isPending) return;
    if (!v) {
      setNote("");
      setError(null);
    }
    onOpenChange(v);
  }

  async function onConfirm() {
    setError(null);
    try {
      await mutation.mutateAsync({
        kind: "DECLARE_UNREPAIRABLE",
        note: note.trim() || null,
      });
      toast.success("已故障报废");
      setNote("");
      onOpenChange(false);
    } catch (err) {
      setError(toFriendlyMessage(err));
    }
  }

  return (
    <AlertDialog open={open} onOpenChange={handleOpenChange}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <div className="flex items-center gap-2">
            <span className="inline-flex items-center gap-1.5 rounded-full bg-destructive/15 px-2.5 py-1 text-xs font-medium text-destructive">
              <ShieldOff className="size-3.5" aria-hidden />
              故障报废
            </span>
          </div>
          <AlertDialogTitle>故障报废</AlertDialogTitle>
          <AlertDialogDescription>
            将"{assetName}"标记为故障报废（送修 → 故障）。后续可走退役、注销或故障解除。
          </AlertDialogDescription>
        </AlertDialogHeader>

        {error && <InlineErrorBanner message={error} />}

        <div className="space-y-2">
          <Label htmlFor="declare-unrepairable-note">判定备注（可选）</Label>
          <Textarea
            id="declare-unrepairable-note"
            value={note}
            onChange={(e) => setNote(e.target.value)}
            placeholder="判定备注（可选）"
            disabled={mutation.isPending}
            rows={3}
          />
        </div>

        <AlertDialogFooter>
          <AlertDialogCancel disabled={mutation.isPending}>
            取消
          </AlertDialogCancel>
          <AlertDialogAction onClick={onConfirm} disabled={mutation.isPending}>
            {mutation.isPending ? "提交中…" : "确认故障报废"}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
