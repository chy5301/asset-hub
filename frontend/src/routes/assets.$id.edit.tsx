import { createFileRoute } from '@tanstack/react-router';
import { z } from 'zod';
import { AssetEditForm } from '@/features/assets/form/asset-edit-form';

export const Route = createFileRoute('/assets/$id/edit')({
  parseParams: ({ id }) => ({ id: z.string().uuid().parse(id) }),
  component: AssetEditForm,
});
