import { describe, it, expect, vi } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { z } from "zod";
import { useFormDialog } from "@/features/assets/detail/use-form-dialog";

const schema = z.object({ value: z.string().min(1) });
type FormValues = z.infer<typeof schema>;

describe("useFormDialog", () => {
  it("成功 submit 应调 mutate、触发 onSuccess、关 dialog", async () => {
    const mutateMock = vi.fn().mockResolvedValue({});
    const onSuccessMock = vi.fn();
    const onOpenChange = vi.fn();

    const { result } = renderHook(() =>
      useFormDialog<FormValues>({
        schema,
        defaultValues: { value: "" },
        mutate: mutateMock,
        onSuccess: onSuccessMock,
        onOpenChange,
      }),
    );

    await act(async () => {
      await result.current.onSubmit({ value: "hello" });
    });

    expect(mutateMock).toHaveBeenCalledWith({ value: "hello" });
    expect(onSuccessMock).toHaveBeenCalled();
    expect(onOpenChange).toHaveBeenCalledWith(false);
  });

  it("失败 submit 应 setError('root') 不关 dialog", async () => {
    const mutateMock = vi.fn().mockRejectedValue(new Error("backend fail"));
    const onSuccessMock = vi.fn();
    const onOpenChange = vi.fn();

    const { result } = renderHook(() =>
      useFormDialog<FormValues>({
        schema,
        defaultValues: { value: "" },
        mutate: mutateMock,
        onSuccess: onSuccessMock,
        onOpenChange,
      }),
    );

    await act(async () => {
      await result.current.onSubmit({ value: "hello" });
    });

    expect(result.current.form.formState.errors.root).toBeDefined();
    expect(onOpenChange).not.toHaveBeenCalledWith(false);
    expect(onSuccessMock).not.toHaveBeenCalled();
  });
});
