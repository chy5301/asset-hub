import { createFileRoute } from '@tanstack/react-router';
import { AssetCreateForm } from '@/features/assets/form/asset-create-form';

export const Route = createFileRoute('/assets/new')({
  component: AssetCreateForm,
});
