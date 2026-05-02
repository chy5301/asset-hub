import { createFileRoute, useNavigate } from '@tanstack/react-router';
import { TypeForm } from '@/features/types/form/type-form';

function NewType() {
  const nav = useNavigate();
  return (
    <div className="space-y-6 max-w-3xl">
      <h1 className="text-xl font-semibold">新建类型</h1>
      <TypeForm
        mode="create"
        onSuccess={(t) => nav({ to: '/types/$id', params: { id: t.id } })}
      />
    </div>
  );
}

export const Route = createFileRoute('/types/new')({
  component: NewType,
});
