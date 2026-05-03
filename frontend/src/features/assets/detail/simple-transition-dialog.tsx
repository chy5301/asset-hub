import { CheckCircle2, Sun, Wrench, type LucideIcon } from "lucide-react";
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

type SimpleKind =
  | "SEND_TO_MAINTENANCE"
  | "RECOVER_FROM_MAINTENANCE"
  | "REINSTATE";

interface KindMeta {
  label: string;
  description: string;
  Icon: LucideIcon;
  bgClass: string;
  fgClass: string;
}

const META: Record<SimpleKind, KindMeta> = {
  SEND_TO_MAINTENANCE: {
    label: "送修",
    description: "资产送修后状态变为'维修中'，无法派发。",
    Icon: Wrench,
    bgClass: "bg-status-maintenance/15",
    fgClass: "text-status-maintenance-fg",
  },
  RECOVER_FROM_MAINTENANCE: {
    label: "维修完成",
    description: "维修完成后资产回到'闲置'状态。",
    Icon: CheckCircle2,
    bgClass: "bg-status-idle/15",
    fgClass: "text-status-idle-fg",
  },
  REINSTATE: {
    label: "重新启用",
    description: "重新启用退役资产，回到'闲置'状态。",
    Icon: Sun,
    bgClass: "bg-status-idle/15",
    fgClass: "text-status-idle-fg",
  },
};

const schema = z.object({
  to_holder: z.string().optional(),
  to_location: z.string().optional(),
  note: z.string().optional(),
});
type FormValues = z.infer<typeof schema>;

interface SimpleTransitionDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  assetId: string;
  kind: SimpleKind;
}

export function SimpleTransitionDialog({
  open,
  onOpenChange,
  assetId,
  kind,
}: SimpleTransitionDialogProps) {
  const meta = META[kind];
  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { to_holder: "", to_location: "", note: "" },
    mode: "onSubmit",
  });
  const mutation = useRecordTransitionMutation(assetId);
  const Icon = meta.Icon;

  function handleOpenChange(v: boolean) {
    if (mutation.isPending) return;
    if (!v) form.reset();
    onOpenChange(v);
  }

  async function onConfirm() {
    const values = form.getValues();
    try {
      await mutation.mutateAsync({
        kind,
        to_holder: values.to_holder?.trim() || null,
        to_location: values.to_location?.trim() || null,
        note: values.note?.trim() || null,
      });
      toast.success(`已${meta.label}`);
      form.reset();
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
            <span
              className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium ${meta.bgClass} ${meta.fgClass}`}
            >
              <Icon className="size-3.5" aria-hidden />
              {meta.label}
            </span>
          </div>
          <AlertDialogTitle>{meta.label}资产</AlertDialogTitle>
          <AlertDialogDescription>{meta.description}</AlertDialogDescription>
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
                  <FormLabel>保管人（可选）</FormLabel>
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
          <AlertDialogAction
            onClick={onConfirm}
            disabled={mutation.isPending}
          >
            {mutation.isPending ? "处理中…" : `确认${meta.label}`}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
