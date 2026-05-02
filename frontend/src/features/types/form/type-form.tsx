import { useEffect, useMemo } from 'react';
import { useForm, FormProvider } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Form, FormField, FormItem, FormLabel, FormControl, FormMessage } from '@/components/ui/form';
import { InlineErrorBanner } from '@/components/feedback/inline-error-banner';
import { useCreateTypeMutation, useUpdateTypeMutation } from '@/api/hooks/types';
import { toFriendlyMessage } from '@/lib/error';
import { buildTypeSchema, type CreateTypeFormValues } from './build-type-schema';
import { CustomFieldsBuilder } from './custom-fields-builder/builder';
import type { components } from '@/api/generated/schema';

type TypeRead = components['schemas']['TypeRead'];

interface Props {
  mode: 'create' | 'edit';
  initial?: TypeRead;
  onSuccess: (t: TypeRead) => void;
}

const CREATE_SCHEMA = buildTypeSchema({ mode: 'create' });
const EDIT_SCHEMA = buildTypeSchema({ mode: 'edit' });

export function TypeForm({ mode, initial, onSuccess }: Props) {
  const schema = mode === 'create' ? CREATE_SCHEMA : EDIT_SCHEMA;
  const createMut = useCreateTypeMutation();
  const updateMut = useUpdateTypeMutation();
  const mutation = mode === 'create' ? createMut : updateMut;

  const form = useForm<CreateTypeFormValues>({
    resolver: zodResolver(schema),
    defaultValues: useMemo(
      () => ({
        name: initial?.name ?? '',
        code_prefix: initial?.code_prefix ?? '',
        description: initial?.description ?? '',
        custom_fields: (initial?.custom_fields ?? []) as never,
      }),
      [initial],
    ),
  });

  useEffect(() => {
    if (initial) {
      form.reset({
        name: initial.name,
        code_prefix: initial.code_prefix,
        description: initial.description ?? '',
        custom_fields: (initial.custom_fields ?? []) as never,
      });
    }
  }, [initial, form]);

  async function onSubmit(values: CreateTypeFormValues) {
    try {
      if (mode === 'create') {
        const res = await createMut.mutateAsync({
          name: values.name,
          code_prefix: (values as { code_prefix: string }).code_prefix,
          description: values.description || undefined,
          custom_fields: values.custom_fields as never,
        });
        onSuccess(res);
      } else if (initial) {
        const body: { name?: string; description?: string | null; custom_fields?: unknown } = {};
        if (values.name !== initial.name) body.name = values.name;
        if ((values.description ?? '') !== (initial.description ?? ''))
          body.description = values.description || null;
        body.custom_fields = values.custom_fields;
        const res = await updateMut.mutateAsync({ id: initial.id, body });
        onSuccess(res);
      }
    } catch (e) {
      const msg = toFriendlyMessage(e);
      if (msg.includes('code_prefix')) {
        form.setError('code_prefix' as never, { message: msg });
      } else if (msg.includes('名称') || msg.includes('name')) {
        form.setError('name', { message: msg });
      } else {
        form.setError('root', { message: msg });
      }
    }
  }

  const submitting = mutation.isPending;
  const submitLabel = submitting
    ? mode === 'create' ? '创建中…' : '保存中…'
    : '保存';

  return (
    <FormProvider {...form}>
      <Form {...form}>
        <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-10">
          {form.formState.errors.root && (
            <InlineErrorBanner message={form.formState.errors.root.message ?? ''} />
          )}

          <section className="space-y-4">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-foreground border-b pb-1.5">
              基本信息
            </h2>

            {/* FormLabel 的 htmlFor 指向 FormControl 注入的 formItemId，不需要手动 id */}
            <FormField
              control={form.control}
              name="name"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>name *</FormLabel>
                  <FormControl>
                    <Input {...field} placeholder="如：笔记本" />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            {mode === 'create' ? (
              <FormField
                control={form.control}
                name={'code_prefix' as never}
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>code_prefix *</FormLabel>
                    <FormControl>
                      <Input {...field} placeholder="2-4 大写字母" className="font-mono" />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            ) : (
              <div>
                {/* edit 模式 code_prefix 只读展示，不参与表单提交 */}
                <Label htmlFor="code_prefix-readonly">code_prefix</Label>
                <Input
                  id="code_prefix-readonly"
                  value={initial?.code_prefix ?? ''}
                  readOnly
                  className="font-mono bg-muted text-muted-foreground"
                />
                <p className="text-xs text-muted-foreground mt-1">创建后不可修改</p>
              </div>
            )}

            <FormField
              control={form.control}
              name="description"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>description</FormLabel>
                  <FormControl>
                    <Textarea {...field} value={field.value ?? ''} rows={2} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
          </section>

          <section className="space-y-4">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-foreground border-b pb-1.5">
              自定义字段
            </h2>
            <CustomFieldsBuilder
              control={form.control}
              setValue={form.setValue}
              errors={form.formState.errors}
            />
          </section>

          <div className="flex items-center justify-end gap-3">
            <Button type="button" variant="outline" onClick={() => history.back()}>
              取消
            </Button>
            <Button type="submit" disabled={submitting}>
              {submitLabel}
            </Button>
          </div>
        </form>
      </Form>
    </FormProvider>
  );
}
