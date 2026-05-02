import { createFileRoute } from '@tanstack/react-router';
import { TypeDetailPage } from '@/features/types/detail/type-detail-page';

function TypeDetailRoute() {
  const { id } = Route.useParams();
  return (
    <div className="max-w-3xl">
      <TypeDetailPage id={id} />
    </div>
  );
}

export const Route = createFileRoute('/types/$id')({
  component: TypeDetailRoute,
});
