import { Shuffle } from "lucide-react";
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
  FormMessage,
} from "@/components/ui/form";
import { InlineErrorBanner } from "@/components/feedback/inline-error-banner";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { toFriendlyMessage } from "@/lib/error";

export function reassignSchema(
  currentHolder: string | null,
  currentLocation: string | null,
) {
  return z
    .object({
      to_holder: z.string().optional(),
      to_location: z.string().optional(),
      note: z.string().optional(),
    })
    .refine(
      (data) => {
        const holderChanged =
          (data.to_holder ?? "") !== (currentHolder ?? "");
        const locationChanged =
          (data.to_location ?? "") !== (currentLocation ?? "");
        return holderChanged || locationChanged;
      },
      {
        message: "必须修改持有人或位置至少一项",
        path: ["to_holder"],
      },
    );
}

type FormValues = z.infer<ReturnType<typeof reassignSchema>>;

interface ReassignDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  assetId: string;
  currentHolder: string | null;
  currentLocation: string | null;
}

export function ReassignDialog({
  open,
  onOpenChange,
  assetId,
  currentHolder,
  currentLocation,
}: ReassignDialogProps) {
  const form = useForm<FormValues>({
    resolver: zodResolver(reassignSchema(currentHolder, currentLocation)),
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
    const valid = await form.trigger();
    if (!valid) return;
    const values = form.getValues();
    try {
      const payload: Record<string, string | null | undefined> = {
        kind: "REASSIGN",
      };
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
      toast.success("已重新分配");
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
            <span className="inline-flex items-center gap-1.5 rounded-full bg-muted px-2.5 py-1 text-xs font-medium text-muted-foreground">
              <Shuffle className="size-3.5" aria-hidden />
              重新分配
            </span>
          </div>
          <AlertDialogTitle>重新分配</AlertDialogTitle>
          <AlertDialogDescription>
            修改持有人或位置（至少一项）。资产状态不变。
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
                  <FormLabel>持有人</FormLabel>
                  <FormControl>
                    <Input {...field} disabled={mutation.isPending} />
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
                  <FormLabel>位置</FormLabel>
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
            {mutation.isPending ? "提交中…" : "确认"}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
