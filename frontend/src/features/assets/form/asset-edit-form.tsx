import { useEffect, useMemo } from 'react';
import { type Control, useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { useNavigate, useParams } from '@tanstack/react-router';
import { Button } from '@/components/ui/button';
import { Form } from '@/components/ui/form';
import { InlineErrorBanner } from '@/components/feedback/inline-error-banner';
import { useAssetTypesQuery } from '@/api/hooks/types';
import { useAssetDetailQuery, useUpdateAsset } from '@/api/hooks/assets';
import { toFriendlyMessage } from '@/lib/error';
import { AssetFormFields } from './asset-form-fields';
import { buildEditSchema, type EditFormValues } from './build-edit-schema';
import { PENDING_TEXT } from './form-toast';
import type { FieldDef } from './types';

export function AssetEditForm() {
  const { id } = useParams({ from: '/assets/$id/edit' });
  const navigate = useNavigate({ from: '/assets/$id/edit' });
  const detailQuery = useAssetDetailQuery(id);
  const typesQuery = useAssetTypesQuery();
  const types = useMemo(() => typesQuery.data ?? [], [typesQuery.data]);
  const mutation = useUpdateAsset(id);

  const asset = detailQuery.data;
  const selectedType = useMemo(
    () => (asset ? types.find((t) => t.id === asset.type_id) : undefined),
    [asset, types],
  );
  const fieldDefs = useMemo<FieldDef[]>(
    () => (selectedType?.custom_fields ?? []) as FieldDef[],
    [selectedType],
  );
  const editSchema = useMemo(() => buildEditSchema(fieldDefs), [fieldDefs]);

  const form = useForm<EditFormValues>({
    resolver: zodResolver(editSchema),
    defaultValues: {
      name: '',
      serial_number: '',
      acquired_at: '',
      holder: '',
      location: '',
      notes: '',
      custom_data: {},
    },
    mode: 'onSubmit',
  });

  // 数据到位后 reset 表单
  useEffect(() => {
    if (asset) {
      form.reset({
        name: asset.name,
        serial_number: asset.serial_number ?? '',
        acquired_at: asset.acquired_at ?? '',
        holder: asset.holder ?? '',
        location: asset.location ?? '',
        notes: asset.notes ?? '',
        custom_data: (asset.custom_data ?? {}) as never,
      });
    }
  }, [asset, form]);

  async function onSubmit(values: EditFormValues) {
    const parsed = editSchema.safeParse(values);
    if (!parsed.success) {
      for (const issue of parsed.error.issues) {
        form.setError(issue.path.join('.') as never, { message: issue.message });
      }
      return;
    }
    try {
      await mutation.mutateAsync({
        name: parsed.data.name,
        serial_number: parsed.data.serial_number || null,
        acquired_at: parsed.data.acquired_at || null,
        holder: parsed.data.holder || null,
        location: parsed.data.location || null,
        notes: parsed.data.notes || null,
        custom_data: parsed.data.custom_data ?? {},
      });
      navigate({ to: '/assets/$id', params: { id } });
    } catch (err) {
      form.setError('root', { message: toFriendlyMessage(err) });
    }
  }

  if (detailQuery.isLoading || typesQuery.isLoading)
    return <div className="text-muted-foreground">加载…</div>;
  if (detailQuery.isError)
    return <InlineErrorBanner message={toFriendlyMessage(detailQuery.error)} />;
  if (!asset) return null;

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <h1 className="text-2xl font-semibold">编辑资产</h1>

      {form.formState.errors.root && (
        <InlineErrorBanner message={String(form.formState.errors.root.message)} />
      )}

      <Form {...form}>
        <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-10">
          <AssetFormFields
            control={form.control as unknown as Control}
            types={types}
            mode="edit"
            assetCode={asset.asset_code}
            forceTypeId={asset.type_id}
          />

          <div className="flex justify-end gap-3 border-t pt-6">
            <Button
              type="button"
              variant="ghost"
              onClick={() => navigate({ to: '/assets/$id', params: { id } })}
            >
              取消
            </Button>
            <Button type="submit" disabled={mutation.isPending}>
              {mutation.isPending ? PENDING_TEXT.UPDATE : '保存'}
            </Button>
          </div>
        </form>
      </Form>
    </div>
  );
}
