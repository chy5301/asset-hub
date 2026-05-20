import { Undo2 } from "lucide-react";
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
import { useFormDialog } from "./use-form-dialog";

const schema = z.object({
  to_holder: z.string().optional(),
  to_location: z.string().optional(),
  note: z.string().optional(),
});
type FormValues = z.infer<typeof schema>;

interface ReturnDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  assetId: string;
}

export function ReturnDialog({
  open,
  onOpenChange,
  assetId,
}: ReturnDialogProps) {
  const mutation = useRecordTransitionMutation(assetId);
  const { form, onSubmit, handleOpenChange } = useFormDialog<FormValues>({
    schema,
    defaultValues: { to_holder: "", to_location: "", note: "" },
    mutate: (values) =>
      mutation.mutateAsync({
        kind: "RETURN",
        to_holder: values.to_holder?.trim() || null,
        to_location: values.to_location?.trim() || null,
        note: values.note?.trim() || null,
      }),
    onSuccess: () => toast.success("已归还"),
    onOpenChange,
  });

  return (
    <Dialog open={open} onOpenChange={(v) => handleOpenChange(v, mutation.isPending)}>
      <DialogContent>
        <DialogHeader>
          <div className="flex items-center gap-2">
            <span className="inline-flex items-center gap-1.5 rounded-full bg-status-idle/15 px-2.5 py-1 text-xs font-medium text-status-idle-fg">
              <Undo2 className="size-3.5" aria-hidden />
              归还
            </span>
          </div>
          <DialogTitle>归还资产</DialogTitle>
          <DialogDescription>
            归还接收人将成为新 holder；不填则资产无 holder（无人值守）。
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
              name="to_holder"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>归还给（可选，留空表示无人值守）</FormLabel>
                  <FormControl>
                    <Input
                      {...field}
                      placeholder="如：仓管李四"
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
                  <FormLabel>归还位置（可选）</FormLabel>
                  <FormControl>
                    <Input
                      {...field}
                      placeholder="如：1F-柜 3"
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
                onClick={() => handleOpenChange(false, mutation.isPending)}
                disabled={mutation.isPending}
              >
                取消
              </Button>
              <Button type="submit" disabled={mutation.isPending}>
                {mutation.isPending ? "归还中…" : "确认归还"}
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
}
