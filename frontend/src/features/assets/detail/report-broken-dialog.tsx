import { AlertTriangle } from "lucide-react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { toast } from "sonner";
import { z } from "zod";

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
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
} from "@/components/ui/form";
import { InlineErrorBanner } from "@/components/feedback/inline-error-banner";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { toFriendlyMessage } from "@/lib/error";

const schema = z.object({
  to_holder: z.string().optional(),
  to_location: z.string().optional(),
  note: z.string().optional(),
});
type FormValues = z.infer<typeof schema>;

interface ReportBrokenDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  assetId: string;
  currentHolder: string | null;
  currentLocation: string | null;
}

export function ReportBrokenDialog({
  open,
  onOpenChange,
  assetId,
  currentHolder,
  currentLocation,
}: ReportBrokenDialogProps) {
  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      to_holder: currentHolder ?? "",
      to_location: currentLocation ?? "",
      note: "",
    },
    mode: "onSubmit",
  });
  const mutation = useRecordTransitionMutation(assetId);

  function handleOpenChange(v: boolean) {
    if (mutation.isPending) return;
    if (!v) {
      form.reset({
        to_holder: currentHolder ?? "",
        to_location: currentLocation ?? "",
        note: "",
      });
    }
    onOpenChange(v);
  }

  async function onConfirm() {
    const values = form.getValues();
    try {
      const payload: Record<string, string | null | undefined> = {
        kind: "REPORT_BROKEN",
      };
      // keep rule：仅传变化字段，不变字段不传保留当前
      if ((values.to_holder ?? "") !== (currentHolder ?? "")) {
        payload.to_holder = (values.to_holder ?? "").trim() || null;
      }
      if ((values.to_location ?? "") !== (currentLocation ?? "")) {
        payload.to_location = (values.to_location ?? "").trim() || null;
      }
      if (values.note?.trim()) {
        payload.note = values.note.trim();
      }
      await mutation.mutateAsync(
        payload as Parameters<typeof mutation.mutateAsync>[0],
      );
      toast.success("已标记故障");
      form.reset({
        to_holder: currentHolder ?? "",
        to_location: currentLocation ?? "",
        note: "",
      });
      onOpenChange(false);
    } catch (err) {
      form.setError("root", { message: toFriendlyMessage(err) });
    }
  }

  return (
    <AlertDialog open={open} onOpenChange={handleOpenChange}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <div className="flex items-center gap-2">
            <span className="inline-flex items-center gap-1.5 rounded-full bg-status-broken/15 px-2.5 py-1 text-xs font-medium text-status-broken-fg">
              <AlertTriangle className="size-3.5" aria-hidden />
              出现故障
            </span>
          </div>
          <AlertDialogTitle>标记出现故障</AlertDialogTitle>
          <AlertDialogDescription>
            标记后资产状态变为"故障"。持有人/位置默认保留。
          </AlertDialogDescription>
        </AlertDialogHeader>

        {form.formState.errors.root && (
          <InlineErrorBanner
            message={String(form.formState.errors.root.message)}
          />
        )}

        <Form {...form}>
          <form className="space-y-4">
            <FormField
              control={form.control}
              name="to_holder"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>持有人（可选）</FormLabel>
                  <FormControl>
                    <Input {...field} disabled={mutation.isPending} />
                  </FormControl>
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
                    <Input {...field} disabled={mutation.isPending} />
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
          </form>
        </Form>

        <AlertDialogFooter>
          <AlertDialogCancel disabled={mutation.isPending}>
            取消
          </AlertDialogCancel>
          <AlertDialogAction onClick={onConfirm} disabled={mutation.isPending}>
            {mutation.isPending ? "提交中…" : "确认标记"}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
