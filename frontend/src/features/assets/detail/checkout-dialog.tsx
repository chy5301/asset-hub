import { useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { InlineErrorBanner } from "@/components/feedback/inline-error-banner";
import { useCheckoutMutation } from "@/api/hooks/checkouts";
import { toFriendlyMessage } from "@/lib/error";
import {
  CHECKOUT_DIALOG_TITLE,
  CHECKOUT_PENDING_TEXT,
  CHECKOUT_VERB,
} from "./checkout-actions";

interface CheckoutDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  assetId: string;
}

export function CheckoutDialog({
  open,
  onOpenChange,
  assetId,
}: CheckoutDialogProps) {
  const [holder, setHolder] = useState("");
  const [location, setLocation] = useState("");
  const [note, setNote] = useState("");
  const [holderError, setHolderError] = useState("");
  const [submitError, setSubmitError] = useState("");

  const mutation = useCheckoutMutation();

  function reset() {
    setHolder("");
    setLocation("");
    setNote("");
    setHolderError("");
    setSubmitError("");
  }

  function handleOpenChange(v: boolean) {
    if (mutation.isPending) return;
    if (!v) reset();
    onOpenChange(v);
  }

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!holder.trim()) {
      setHolderError("请填写保管人");
      return;
    }
    setHolderError("");
    setSubmitError("");
    try {
      await mutation.mutateAsync({
        assetId,
        body: {
          holder: holder.trim(),
          location: location.trim() || null,
          note: note.trim() || null,
        },
      });
      reset();
      onOpenChange(false);
    } catch (err) {
      setSubmitError(toFriendlyMessage(err));
    }
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{CHECKOUT_DIALOG_TITLE}</DialogTitle>
          <DialogDescription>
            填写保管人后确认，派发记录会自动写入流转历史。
          </DialogDescription>
        </DialogHeader>

        {submitError && <InlineErrorBanner message={submitError} />}

        <form onSubmit={onSubmit} className="space-y-4">
          <div className="space-y-1.5">
            <label htmlFor="checkout-holder" className="text-sm font-medium">
              保管人 <span className="text-destructive">*</span>
            </label>
            <Input
              id="checkout-holder"
              value={holder}
              onChange={(e) => setHolder(e.target.value)}
              disabled={mutation.isPending}
              autoFocus
              aria-invalid={holderError ? true : undefined}
              aria-describedby={holderError ? "checkout-holder-err" : undefined}
            />
            {holderError && (
              <p id="checkout-holder-err" className="text-xs text-destructive">
                {holderError}
              </p>
            )}
          </div>

          <div className="space-y-1.5">
            <label htmlFor="checkout-location" className="text-sm font-medium">
              位置
            </label>
            <Input
              id="checkout-location"
              value={location}
              onChange={(e) => setLocation(e.target.value)}
              disabled={mutation.isPending}
            />
          </div>

          <div className="space-y-1.5">
            <label htmlFor="checkout-note" className="text-sm font-medium">
              备注
            </label>
            <Textarea
              id="checkout-note"
              value={note}
              onChange={(e) => setNote(e.target.value)}
              disabled={mutation.isPending}
              rows={3}
            />
          </div>

          <DialogFooter>
            <Button
              type="button"
              variant="ghost"
              onClick={() => handleOpenChange(false)}
              disabled={mutation.isPending}
            >
              取消
            </Button>
            <Button type="submit" disabled={mutation.isPending}>
              {mutation.isPending ? CHECKOUT_PENDING_TEXT : `确认${CHECKOUT_VERB}`}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
