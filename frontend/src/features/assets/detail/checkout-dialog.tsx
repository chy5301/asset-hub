import { ArrowRightFromLine, CalendarIcon, type LucideIcon } from "lucide-react";
import { format, startOfDay } from "date-fns";
import { zhCN } from "date-fns/locale";
import { toast } from "sonner";
import { z } from "zod";

import { useRecordTransitionMutation } from "@/api/hooks/transitions";
import { Button } from "@/components/ui/button";
import { Calendar } from "@/components/ui/calendar";
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
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { InlineErrorBanner } from "@/components/feedback/inline-error-banner";
import { Input } from "@/components/ui/input";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";
import type { CheckoutKind } from "./available-transitions";
import { useFormDialog } from "./use-form-dialog";

const META: Record<CheckoutKind, { verb: string; Icon: LucideIcon; audience: string }> = {
  CHECKOUT_INTERNAL: { verb: "派发", Icon: ArrowRightFromLine, audience: "团队成员" },
  CHECKOUT_EXTERNAL: { verb: "出借", Icon: ArrowRightFromLine, audience: "外部人员" },
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
  const mutation = useRecordTransitionMutation(assetId);
  const { form, onSubmit, handleOpenChange } = useFormDialog<FormValues>({
    schema,
    defaultValues: { to_holder: "", to_location: "", note: "" },
    mutate: (values) =>
      mutation.mutateAsync({
        kind,
        to_holder: values.to_holder.trim(),
        to_location: values.to_location?.trim() || null,
        due_at: values.due_at ? `${values.due_at}T00:00:00` : null,
        note: values.note?.trim() || null,
      }),
    onSuccess: () => toast.success(`已${meta.verb}`),
    onOpenChange,
  });

  return (
    <Dialog open={open} onOpenChange={(v) => handleOpenChange(v, mutation.isPending)}>
      <DialogContent>
        <DialogHeader>
          <div className="flex items-center gap-2">
            <span
              className={cn(
                "inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium",
                kind === "CHECKOUT_INTERNAL"
                  ? "bg-status-in-use/15 text-status-in-use-fg"
                  : "bg-status-borrowed/15 text-status-borrowed-fg",
              )}
            >
              <Icon className="size-3.5" aria-hidden />
              {meta.verb}
            </span>
          </div>
          <DialogTitle>{meta.verb}资产</DialogTitle>
          <DialogDescription>{meta.verb}给{meta.audience}。</DialogDescription>
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
                    {meta.verb}给 <span className="text-destructive">*</span>
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
                  <Popover>
                    <PopoverTrigger asChild>
                      <FormControl>
                        <Button
                          variant="outline"
                          className={cn(
                            "w-full justify-start text-left font-normal",
                            !field.value && "text-muted-foreground",
                          )}
                          disabled={mutation.isPending}
                        >
                          <CalendarIcon className="mr-2 h-4 w-4" />
                          {field.value
                            ? format(new Date(field.value), "yyyy-MM-dd", { locale: zhCN })
                            : "选择日期"}
                        </Button>
                      </FormControl>
                    </PopoverTrigger>
                    <PopoverContent className="w-auto p-0" align="start">
                      <Calendar
                        mode="single"
                        selected={field.value ? new Date(field.value) : undefined}
                        onSelect={(d) => field.onChange(d ? format(d, "yyyy-MM-dd") : undefined)}
                        disabled={(d) => d < startOfDay(new Date())}
                        initialFocus
                      />
                    </PopoverContent>
                  </Popover>
                  <FormDescription className="text-xs">
                    建议填写以启用超期提醒；留空则不预警
                  </FormDescription>
                  <FormMessage />
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
                {mutation.isPending ? `${meta.verb}中…` : `确认${meta.verb}`}
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
}
