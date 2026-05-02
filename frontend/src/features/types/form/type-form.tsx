import { useEffect, useMemo } from 'react';
import { useForm, type Resolver } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { useNavigate } from '@tanstack/react-router';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Form, FormField, FormItem, FormLabel, FormControl, FormMessage } from '@/components/ui/form';
import { InlineErrorBanner } from '@/components/feedback/inline-error-banner';
import { useCreateTypeMutation, useUpdateTypeMutation } from '@/api/hooks/types';
import { toFriendlyMessage, isHttpError } from '@/lib/error';
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
  const navigate = useNavigate();
  const createMut = useCreateTypeMutation();
  const updateMut = useUpdateTypeMutation();
  const mutation = mode === 'create' ? createMut : updateMut;

  const form = useForm<CreateTypeFormValues>({
    // 与 asset-create-form 同款 §J/§L cast：buildTypeSchema 条件 .extend 让 zod 推导
    // 在 'create' 分支的 input/output 类型与手写 CreateTypeFormValues 不完全 unify
    // （fieldDefSchema 的 required: .default(false) 令 input 为 boolean|undefined，
    // output 为 boolean；RHF Resolver<TFieldValues,_,TInput> 三参数分离暴露此分歧）
    resolver: zodResolver(schema) as unknown as Resolver<CreateTypeFormValues>,
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

  // 异步获取的 initial 到达后回填表单；form 引用 RHF 7.x 内部稳定，仅为满足 exhaustive-deps
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
        type TypeUpdateBody = components['schemas']['TypeUpdate'];
        const body: TypeUpdateBody = {};
        if (values.name !== initial.name) body.name = values.name;
        if ((values.description ?? '') !== (initial.description ?? ''))
          body.description = values.description || null;
        // custom_fields 形状在运行时与 CustomFieldDef[] 兼容；类型上需 cast（§J/§L）
        body.custom_fields = values.custom_fields as TypeUpdateBody['custom_fields'];
        const res = await updateMut.mutateAsync({ id: initial.id, body });
        onSuccess(res);
      }
    } catch (e) {
      const msg = toFriendlyMessage(e);
      const is409 = isHttpError(e) && e.status === 409;
      if (is409 && msg.includes('code_prefix')) {
        form.setError('code_prefix' as never, { message: msg });
      } else if (is409 && (msg.includes('名称') || msg.includes('name'))) {
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
            <Button type="button" variant="outline" onClick={() => navigate({ to: '/types' })}>
              取消
            </Button>
            <Button type="submit" disabled={submitting}>
              {submitLabel}
            </Button>
          </div>
        </form>
    </Form>
  );
}
