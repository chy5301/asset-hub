import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
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
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { InlineErrorBanner } from "@/components/feedback/inline-error-banner";
import { useCheckoutMutation } from "@/api/hooks/checkouts";
import { toFriendlyMessage } from "@/lib/error";
import {
  CHECKOUT_DIALOG_TITLE,
  CHECKOUT_PENDING_TEXT,
  CHECKOUT_VERB,
} from "./checkout-actions";

const schema = z.object({
  holder: z.string().min(1, "保管人必填"),
  location: z.string().optional(),
  note: z.string().optional(),
});
type Values = z.infer<typeof schema>;

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
  const mutation = useCheckoutMutation();
  const form = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: { holder: "", location: "", note: "" },
    mode: "onSubmit",
  });

  function handleOpenChange(v: boolean) {
    if (mutation.isPending) return;
    if (!v) form.reset();
    onOpenChange(v);
  }

  async function onSubmit(values: Values) {
    try {
      await mutation.mutateAsync({
        assetId,
        body: {
          holder: values.holder.trim(),
          location: values.location?.trim() || null,
          note: values.note?.trim() || null,
        },
      });
      form.reset();
      onOpenChange(false);
    } catch (err) {
      form.setError("root", { message: toFriendlyMessage(err) });
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

        {form.formState.errors.root && (
          <InlineErrorBanner
            message={String(form.formState.errors.root.message)}
          />
        )}

        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
            <FormField
              control={form.control}
              name="holder"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>
                    保管人 <span className="text-destructive">*</span>
                  </FormLabel>
                  <FormControl>
                    <Input
                      {...field}
                      disabled={mutation.isPending}
                      autoFocus
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="location"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>位置</FormLabel>
                  <FormControl>
                    <Input {...field} disabled={mutation.isPending} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="note"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>备注</FormLabel>
                  <FormControl>
                    <Textarea
                      {...field}
                      disabled={mutation.isPending}
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
              <Button type="submit" disabled={mutation.isPending}>
                {mutation.isPending
                  ? CHECKOUT_PENDING_TEXT
                  : `确认${CHECKOUT_VERB}`}
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
}
