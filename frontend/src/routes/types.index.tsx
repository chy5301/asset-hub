import { createFileRoute } from '@tanstack/react-router';
import { TypesPage } from '@/features/types/list/types-page';

export const Route = createFileRoute('/types/')({
  component: TypesPage,
});
