import { useEffect, useMemo } from 'react';
import { useForm, useWatch, type Resolver } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { Link, useNavigate } from '@tanstack/react-router';
import { Button } from '@/components/ui/button';
import { Form } from '@/components/ui/form';
import { InlineErrorBanner } from '@/components/feedback/inline-error-banner';
import { useAssetTypesQuery } from '@/api/hooks/types';
import { useCreateAsset } from '@/api/hooks/assets';
import { toFriendlyMessage } from '@/lib/error';
import { AssetFormFields } from './asset-form-fields';
import { buildAssetSchema, type CreateFormValues } from './build-asset-schema';
import { PENDING_TEXT } from './form-toast';
import type { FieldDef } from './types';
import { DEFAULT_SORT } from '@/features/assets/list/search-schema';

// 模块级常量：避免每次 render 都重建空 schema
const CREATE_EMPTY_SCHEMA = buildAssetSchema([], { mode: 'create' });

export function AssetCreateForm() {
  const navigate = useNavigate({ from: '/assets/new' });
  const typesQuery = useAssetTypesQuery();
  const types = useMemo(() => typesQuery.data ?? [], [typesQuery.data]);
  const mutation = useCreateAsset();

  const form = useForm<CreateFormValues>({
    // zodResolver 推导走 buildAssetSchema 返回 union 的窄分支（不含 type_id），
    // 与手写 CreateFormValues（强制带 type_id）不 unify——保留最小 cast。
    resolver: zodResolver(CREATE_EMPTY_SCHEMA) as unknown as Resolver<CreateFormValues>,
    defaultValues: {
      name: '',
      type_id: '',
      model: '',
      serial_number: '',
      acquired_at: '',
      holder: '',
      location: '',
      notes: '',
      custom_data: {},
    },
    mode: 'onSubmit',
  });

  const selectedTypeId = useWatch({ control: form.control, name: 'type_id' });
  const selectedType = useMemo(
    () => types.find((t) => t.id === selectedTypeId),
    [types, selectedTypeId],
  );

  // type 切换时重置 custom_data 为该 type 的 default 值
  useEffect(() => {
    if (selectedType) {
      const defs = (selectedType.custom_fields ?? []) as FieldDef[];
      const defaults: Record<string, unknown> = {};
      for (const d of defs) {
        if (d.default !== undefined && d.default !== null) defaults[d.key] = d.default;
      }
      form.setValue('custom_data', defaults as never, { shouldValidate: false });
    } else {
      form.setValue('custom_data', {} as never, { shouldValidate: false });
    }
    // 清掉之前 type 的 custom_data 校验错误
    form.clearErrors();
  }, [selectedType, form]);

  function onInvalid() {
    // 用户漏填必填字段（如 type_id / name）时，react-hook-form 内部 zodResolver
    // 已 setError 到字段；这里补一条顶部 banner，否则按钮看似哑火
    form.setError('root', { message: '请检查表单中标红的字段' });
    requestAnimationFrame(() => {
      const el = document.querySelector('[aria-invalid="true"]');
      el?.scrollIntoView({ behavior: 'smooth', block: 'center' });
    });
  }

  async function onSubmit(values: CreateFormValues) {
    const fieldDefs = (selectedType?.custom_fields ?? []) as FieldDef[];
    const schema = buildAssetSchema(fieldDefs, { mode: 'create' });
    const parsed = schema.safeParse(values);
    if (!parsed.success) {
      // 把 custom_data.* 错误回填到对应字段
      for (const issue of parsed.error.issues) {
        const path = issue.path.join('.');
        form.setError(path as never, { message: issue.message });
      }
      onInvalid();
      return;
    }
    // schema union 推导窄到 edit 分支（无 type_id），cast 回 CreateFormValues
    const data = parsed.data as CreateFormValues;
    try {
      const created = await mutation.mutateAsync({
        name: data.name,
        type_id: data.type_id,
        model: data.model || null,
        serial_number: data.serial_number || null,
        acquired_at: data.acquired_at || null,
        holder: data.holder || null,
        location: data.location || null,
        notes: data.notes || null,
        custom_data: data.custom_data ?? {},
      });
      navigate({ to: '/assets/$id', params: { id: created.id } });
    } catch (err) {
      form.setError('root', { message: toFriendlyMessage(err) });
    }
  }

  if (typesQuery.isLoading) return <div className="text-muted-foreground">加载类型…</div>;
  if (typesQuery.isError) return <InlineErrorBanner message={toFriendlyMessage(typesQuery.error)} />;

  if (types.length === 0) {
    return (
      <div className="mx-auto max-w-2xl space-y-4">
        <h1 className="text-2xl font-semibold">登记新资产</h1>
        <div className="rounded-md border border-amber-200 bg-amber-50 p-4 text-sm dark:border-amber-900 dark:bg-amber-950">
          <p className="font-medium">尚未创建任何类型</p>
          <p className="mt-2 text-muted-foreground">
            资产必须归属于一个类型。请先创建类型，再回来登记资产。
          </p>
          <Button asChild className="mt-3">
            <Link to="/types/new">前往创建类型</Link>
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <h1 className="text-2xl font-semibold">登记新资产</h1>

      {form.formState.errors.root && (
        <InlineErrorBanner message={String(form.formState.errors.root.message)} />
      )}

      <Form {...form}>
        <form onSubmit={form.handleSubmit(onSubmit, onInvalid)} className="space-y-10">
          <AssetFormFields<CreateFormValues> control={form.control} types={types} mode="create" />

          <div className="flex justify-end gap-3 border-t pt-6">
            <Button
              type="button"
              variant="ghost"
              onClick={() => navigate({ to: '/', search: { sort: DEFAULT_SORT, page: 1, pageSize: 50 } })}
            >
              取消
            </Button>
            <Button type="submit" disabled={mutation.isPending}>
              {mutation.isPending ? PENDING_TEXT.CREATE : '登记'}
            </Button>
          </div>
        </form>
      </Form>
    </div>
  );
}
