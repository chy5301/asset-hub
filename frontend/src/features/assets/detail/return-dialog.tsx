import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from '@/components/ui/form';
import { InlineErrorBanner } from '@/components/feedback/inline-error-banner';
import { useReturnMutation } from '@/api/hooks/checkouts';
import { toFriendlyMessage } from '@/lib/error';
import { formatDateTime } from '@/lib/date';
import {
  RETURN_DIALOG_TITLE, RETURN_PENDING_TEXT, RETURN_VERB,
} from './checkout-actions';
import type { components } from '@/api/generated/schema';

type CheckoutRead = components['schemas']['CheckoutRead'];

const schema = z.object({
  note: z.string().optional(),
});
type Values = z.infer<typeof schema>;

interface ReturnDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  assetId: string;
  currentCheckout: CheckoutRead | null;
}

export function ReturnDialog({ open, onOpenChange, assetId, currentCheckout }: ReturnDialogProps) {
  const mutation = useReturnMutation();
  const form = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: { note: '' },
    mode: 'onSubmit',
  });

  function handleOpenChange(v: boolean) {
    if (mutation.isPending) return;
    if (!v) form.reset();
    onOpenChange(v);
  }

  async function onSubmit(values: Values) {
    if (!currentCheckout) return;
    try {
      await mutation.mutateAsync({
        assetId,
        body: { note: values.note?.trim() || null },
      });
      form.reset();
      onOpenChange(false);
    } catch (err) {
      form.setError('root', { message: toFriendlyMessage(err) });
    }
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{RETURN_DIALOG_TITLE}</DialogTitle>
          <DialogDescription>确认归还后会在流转历史中记录归还时间与备注。</DialogDescription>
        </DialogHeader>

        {currentCheckout ? (
          <div className="rounded-sm bg-muted/50 px-3 py-2 text-sm">
            当前派发给 · <strong>{currentCheckout.holder}</strong>
            {currentCheckout.location ? <> · {currentCheckout.location}</> : null}
            <br />
            派发于 ·{' '}
            <time className="font-code">{formatDateTime(currentCheckout.checked_out_at)}</time>
          </div>
        ) : mutation.isIdle ? (
          // 仅在用户尚未提交时提示；mutation success/pending 期间不渲染——
          // 否则成功后 currentCheckout 因 invalidate 变 null，dialog 关闭前会一闪 banner
          <InlineErrorBanner message="此资产当前无派发中记录，请刷新页面。" />
        ) : null}

        {form.formState.errors.root && (
          <InlineErrorBanner message={String(form.formState.errors.root.message)} />
        )}

        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
            <FormField
              control={form.control}
              name="note"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>备注</FormLabel>
                  <FormControl>
                    <Textarea
                      {...field}
                      disabled={mutation.isPending || !currentCheckout}
                      rows={3}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <DialogFooter>
              <Button
                type="button"
                variant="ghost"
                onClick={() => handleOpenChange(false)}
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
        </Form>
      </DialogContent>
    </Dialog>
  );
}
