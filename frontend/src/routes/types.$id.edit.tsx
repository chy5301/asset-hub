import { createFileRoute } from "@tanstack/react-router";
import { TypeEditPage } from "@/features/types/detail/type-edit-page";

function TypeEditRoute() {
  const { id } = Route.useParams();
  return <TypeEditPage id={id} />;
}

export const Route = createFileRoute("/types/$id/edit")({
  component: TypeEditRoute,
});
