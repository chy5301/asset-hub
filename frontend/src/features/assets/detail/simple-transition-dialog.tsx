import {
  AlertTriangle,
  CheckCircle2,
  ShieldCheck,
  Sun,
  Wrench,
  type LucideIcon,
} from "lucide-react";
import { useMemo } from "react";
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
import type { TransitionCreate, TransitionKind } from "@/features/assets/types";

type SimpleKind =
  | "SEND_TO_MAINTENANCE"
  | "RECOVER_FROM_MAINTENANCE"
  | "REINSTATE"
  | "REPORT_BROKEN"
  | "DISMISS";

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
  REPORT_BROKEN: {
    label: "出现故障",
    description: "标记后资产状态变为'故障'。持有人/位置默认保留。",
    Icon: AlertTriangle,
    bgClass: "bg-status-broken/15",
    fgClass: "text-status-broken-fg",
  },
  DISMISS: {
    label: "故障解除",
    description: "资产从故障态回到闲置。持有人/位置默认保留。",
    Icon: ShieldCheck,
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
  currentHolder?: string | null;
  currentLocation?: string | null;
}

export function SimpleTransitionDialog({
  open,
  onOpenChange,
  assetId,
  kind,
  currentHolder,
  currentLocation,
}: SimpleTransitionDialogProps) {
  const meta = META[kind];

  const defaultValues = useMemo(
    () => ({
      to_holder: currentHolder ?? "",
      to_location: currentLocation ?? "",
      note: "",
    }),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [],
  );

  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues,
    mode: "onSubmit",
  });
  const mutation = useRecordTransitionMutation(assetId);
  const Icon = meta.Icon;

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
      const payload: Partial<TransitionCreate> & { kind: TransitionKind } = {
        kind,
      };

      // keep rule：仅传变化字段，不变字段不传，保留当前值
      const holderBaseline = currentHolder ?? "";
      const locationBaseline = currentLocation ?? "";
      if ((values.to_holder ?? "") !== holderBaseline) {
        payload.to_holder = values.to_holder?.trim() || null;
      }
      if ((values.to_location ?? "") !== locationBaseline) {
        payload.to_location = values.to_location?.trim() || null;
      }
      if (values.note?.trim()) {
        payload.note = values.note.trim();
      }

      await mutation.mutateAsync(payload);
      toast.success(`已${meta.label}`);
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
