import { ArrowRightFromLine, Send, type LucideIcon } from "lucide-react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { toast } from "sonner";
import { z } from "zod";

import { useRecordTransitionMutation } from "@/api/hooks/transitions";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { InlineErrorBanner } from "@/components/feedback/inline-error-banner";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { toFriendlyMessage } from "@/lib/error";

type CheckoutKind = "CHECKOUT_INTERNAL" | "CHECKOUT_EXTERNAL";

interface KindMeta {
  chipLabel: string;
  Icon: LucideIcon;
  title: string;
  description: string;
  holderLabel: string;
  submitText: string;
  pendingText: string;
  successText: string;
}

const META: Record<CheckoutKind, KindMeta> = {
  CHECKOUT_INTERNAL: {
    chipLabel: "派发",
    Icon: ArrowRightFromLine,
    title: "派发资产",
    description: "派发给团队成员。",
    holderLabel: "派发给",
    submitText: "确认派发",
    pendingText: "派发中…",
    successText: "已派发",
  },
  CHECKOUT_EXTERNAL: {
    chipLabel: "出借",
    Icon: Send,
    title: "出借资产",
    description: "出借给外部人员。",
    holderLabel: "出借给",
    submitText: "确认出借",
    pendingText: "出借中…",
    successText: "已出借",
  },
};

const schema = z.object({
  to_holder: z.string().min(1, "请输入派发对象"),
  to_location: z.string().optional(),
  due_at: z.string().optional(),
  note: z.string().optional(),
});
type FormValues = z.infer<typeof schema>;

interface CheckoutDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  assetId: string;
  kind: CheckoutKind;
}

export function CheckoutDialog({
  open,
  onOpenChange,
  assetId,
  kind,
}: CheckoutDialogProps) {
  const meta = META[kind];
  const Icon = meta.Icon;
  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      to_holder: "",
      to_location: "",
      note: "",
    },
    mode: "onSubmit",
  });
  const mutation = useRecordTransitionMutation(assetId);

  function handleOpenChange(v: boolean) {
    if (mutation.isPending) return;
    if (!v) form.reset();
    onOpenChange(v);
  }

  async function onSubmit(values: FormValues) {
    try {
      await mutation.mutateAsync({
        kind,
        to_holder: values.to_holder.trim(),
        to_location: values.to_location?.trim() || null,
        due_at: values.due_at || null,
        note: values.note?.trim() || null,
      });
      toast.success(meta.successText);
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
          <div className="flex items-center gap-2">
            <span className="inline-flex items-center gap-1.5 rounded-full bg-status-in-use/15 px-2.5 py-1 text-xs font-medium text-status-in-use-fg">
              <Icon className="size-3.5" aria-hidden />
              {meta.chipLabel}
            </span>
          </div>
          <DialogTitle>{meta.title}</DialogTitle>
          <DialogDescription>{meta.description}</DialogDescription>
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
              name="to_holder"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>
                    {meta.holderLabel} <span className="text-destructive">*</span>
                  </FormLabel>
                  <FormControl>
                    <Input
                      {...field}
                      placeholder="保管人/接收方"
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
              name="to_location"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>位置（可选）</FormLabel>
                  <FormControl>
                    <Input
                      {...field}
                      placeholder="如 1F-工位"
                      disabled={mutation.isPending}
                    />
                  </FormControl>
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="due_at"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>期望归还时间（可选）</FormLabel>
                  <FormControl>
                    <Input
                      type="datetime-local"
                      {...field}
                      disabled={mutation.isPending}
                    />
                  </FormControl>
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="note"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>备注（可选）</FormLabel>
                  <FormControl>
                    <Textarea
                      {...field}
                      disabled={mutation.isPending}
                      rows={3}
                    />
                  </FormControl>
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
                {mutation.isPending ? meta.pendingText : meta.submitText}
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
}
