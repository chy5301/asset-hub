import { useEffect } from 'react';
import { useForm, type Resolver } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { useNavigate } from '@tanstack/react-router';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Form, FormField, FormItem, FormLabel, FormControl, FormMessage } from '@/components/ui/form';
import { SectionCaption } from '@/components/ui/section-heading';
import { InlineErrorBanner } from '@/components/feedback/inline-error-banner';
import { useCreateTypeMutation, useUpdateTypeMutation } from '@/api/hooks/types';
import { toFriendlyMessage, isHttpError } from '@/lib/error';
import { buildTypeSchema, type CreateTypeFormValues } from './build-type-schema';
import { CustomFieldsBuilder } from './custom-fields-builder/builder';
import type { TypeRead, TypeUpdate } from '@/features/assets/types';

type ApiFieldDef = TypeRead['custom_fields'][number];
type RhfFieldDef = Omit<
  ApiFieldDef,
  'label' | 'placeholder' | 'help' | 'unit' | 'min' | 'max' | 'options' | 'displayAs'
> & {
  label?: string;
  placeholder?: string;
  help?: string;
  unit?: string;
  min?: number;
  max?: number;
  options?: string[];
  displayAs?: string;
};

// 必需：API nullable 字段在 zod fieldDefSchema 拒绝 null，reset 前归一化避免 silent submit failure
const NULLABLE_FIELD_KEYS = [
  'label', 'placeholder', 'help', 'unit', 'min', 'max', 'options', 'displayAs',
] as const;

function coerceFieldDefsForRHF(fields: ApiFieldDef[] | null | undefined): RhfFieldDef[] {
  return (fields ?? []).map((f) => {
    const coerced = { ...f } as Record<string, unknown>;
    for (const k of NULLABLE_FIELD_KEYS) {
      if (coerced[k] === null) coerced[k] = undefined;
    }
    return coerced as RhfFieldDef;
  });
}

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
    // zodResolver 推导走 buildTypeSchema 返回 union 的窄分支（custom_fields.required 是 optional），
    // 与手写 CreateTypeFormValues 不 unify——保留最小 cast。
    resolver: zodResolver(schema) as unknown as Resolver<CreateTypeFormValues>,
    defaultValues: {
      name: initial?.name ?? '',
      code_prefix: initial?.code_prefix ?? '',
      description: initial?.description ?? '',
      custom_fields: coerceFieldDefsForRHF(initial?.custom_fields) as never,
    },
  });

  useEffect(() => {
    if (initial) {
      form.reset({
        name: initial.name,
        code_prefix: initial.code_prefix,
        description: initial.description ?? '',
        custom_fields: coerceFieldDefsForRHF(initial.custom_fields) as never,
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
        const body: TypeUpdate = {};
        if (values.name !== initial.name) body.name = values.name;
        if ((values.description ?? '') !== (initial.description ?? ''))
          body.description = values.description || null;
        body.custom_fields = values.custom_fields as TypeUpdate['custom_fields']; // §J/§L cast
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
            <SectionCaption>基本信息</SectionCaption>

            <FormField
              control={form.control}
              name="name"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>名称 *</FormLabel>
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
                    <FormLabel>代号前缀 *</FormLabel>
                    <FormControl>
                      <Input {...field} placeholder="2-4 大写字母" className="font-mono" />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            ) : (
              <div>
                <Label htmlFor="code_prefix-readonly">代号前缀</Label>
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
                  <FormLabel>描述</FormLabel>
                  <FormControl>
                    <Textarea {...field} value={field.value ?? ''} rows={2} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
          </section>

          <section className="space-y-4">
            <SectionCaption>自定义字段</SectionCaption>
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
