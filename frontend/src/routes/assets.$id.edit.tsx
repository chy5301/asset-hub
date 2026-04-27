import { createFileRoute } from '@tanstack/react-router';
import { AssetEditForm } from '@/features/assets/form/asset-edit-form';

export const Route = createFileRoute('/assets/$id/edit')({
  component: AssetEditForm,
});
