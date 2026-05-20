import { useForm, type DefaultValues, type FieldErrors } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import type { ZodTypeAny } from "zod";

import { toFriendlyMessage } from "@/lib/error";

interface UseFormDialogParams<T extends Record<string, unknown>> {
  schema: ZodTypeAny;
  defaultValues: DefaultValues<T>;
  mutate: (values: T) => Promise<unknown>;
  onSuccess?: () => void;
  onOpenChange: (open: boolean) => void;
}

/**
 * M4-A：CheckoutDialog / ReturnDialog 共用的表单 dialog 样板：
 * useForm + zodResolver + onSubmit 含 error 处理 + handleOpenChange。
 *
 * 返回 { form, onSubmit, handleOpenChange }。
 * onSubmit 成功时：调用 mutate(values)，触发 onSuccess、reset form、关 dialog。
 * onSubmit 失败时：setError('root', { message: toFriendlyMessage(err) })，dialog 留开。
 * handleOpenChange 用于 dialog 外层 onOpenChange：mutation 进行中阻止关闭。
 */
export function useFormDialog<T extends Record<string, unknown>>({
  schema,
  defaultValues,
  mutate,
  onSuccess,
  onOpenChange,
}: UseFormDialogParams<T>) {
  const form = useForm<T>({
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    resolver: zodResolver(schema as any),
    defaultValues,
    mode: "onSubmit",
  });

  // Subscribe to errors so that setError('root') triggers a re-render
  // (RHF proxy tracks formState properties accessed during render)
  void (form.formState.errors as FieldErrors<T>);

  async function onSubmit(values: T) {
    try {
      await mutate(values);
      onSuccess?.();
      form.reset();
      onOpenChange(false);
    } catch (err) {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      form.setError("root" as any, { message: toFriendlyMessage(err) });
    }
  }

  function handleOpenChange(v: boolean, isPending: boolean) {
    if (isPending) return;
    if (!v) form.reset();
    onOpenChange(v);
  }

  return { form, onSubmit, handleOpenChange };
}
