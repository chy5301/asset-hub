// frontend/src/features/assets/detail/return-dialog.tsx
import { useEffect, useState } from "react";
import { format, parseISO } from "date-fns";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { useReturnMutation } from "@/api/hooks/checkouts";
import { toFriendlyMessage } from "@/lib/error";
import {
  RETURN_DIALOG_TITLE,
  RETURN_PENDING_TEXT,
  RETURN_VERB,
} from "./checkout-actions";
import type { components } from "@/api/generated/schema";

type CheckoutRead = components["schemas"]["CheckoutRead"];

interface ReturnDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  assetId: string;
  currentCheckout: CheckoutRead | null;
}

export function ReturnDialog({
  open,
  onOpenChange,
  assetId,
  currentCheckout,
}: ReturnDialogProps) {
  const [note, setNote] = useState("");
  const [submitError, setSubmitError] = useState("");
  const mutation = useReturnMutation();

  useEffect(() => {
    if (!open) {
      setNote("");
      setSubmitError("");
    }
  }, [open]);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!currentCheckout) return; // data race 保护：按钮 disabled，不应走到这
    setSubmitError("");
    try {
      await mutation.mutateAsync({
        assetId,
        body: { note: note.trim() || null },
      });
      onOpenChange(false);
    } catch (err) {
      setSubmitError(toFriendlyMessage(err));
    }
  }

  return (
    <Dialog
      open={open}
      onOpenChange={(v) => {
        if (!mutation.isPending) onOpenChange(v);
      }}
    >
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{RETURN_DIALOG_TITLE}</DialogTitle>
          <DialogDescription>
            确认归还后会在流转历史中记录归还时间与备注。
          </DialogDescription>
        </DialogHeader>

        {currentCheckout ? (
          <div className="rounded-sm bg-muted/50 px-3 py-2 text-sm">
            当前派发给 · <strong>{currentCheckout.holder}</strong>
            {currentCheckout.location ? <> · {currentCheckout.location}</> : null}
            <br />
            派发于 ·{" "}
            <time className="font-code">
              {format(parseISO(currentCheckout.checked_out_at), "yyyy-MM-dd HH:mm")}
            </time>
          </div>
        ) : (
          <div
            role="alert"
            className="rounded-sm border border-destructive/50 bg-destructive/10 px-3 py-2 text-sm text-destructive"
          >
            此资产当前无派发中记录，请刷新页面。
          </div>
        )}

        {submitError && (
          <div
            role="alert"
            className="rounded-sm border border-destructive/50 bg-destructive/10 px-3 py-2 text-sm text-destructive"
          >
            {submitError}
          </div>
        )}

        <form onSubmit={onSubmit} className="space-y-4">
          <div className="space-y-1.5">
            <label htmlFor="return-note" className="text-sm font-medium">
              备注（可选）
            </label>
            <textarea
              id="return-note"
              value={note}
              onChange={(e) => setNote(e.target.value)}
              disabled={mutation.isPending || !currentCheckout}
              rows={3}
              className="flex w-full rounded-sm border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
            />
          </div>

          <DialogFooter>
            <Button
              type="button"
              variant="ghost"
              onClick={() => onOpenChange(false)}
              disabled={mutation.isPending}
            >
              取消
            </Button>
            <Button
              type="submit"
              disabled={mutation.isPending || !currentCheckout}
            >
              {mutation.isPending ? RETURN_PENDING_TEXT : `确认${RETURN_VERB}`}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
