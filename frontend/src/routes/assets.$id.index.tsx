import { createFileRoute } from "@tanstack/react-router";
import { AssetDetailPage } from "@/features/assets/detail/asset-detail-page";

export const Route = createFileRoute("/assets/$id/")({
  component: RouteComponent,
});

function RouteComponent() {
  const { id } = Route.useParams();
  return <AssetDetailPage id={id} />;
}
