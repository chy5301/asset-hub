import { createFileRoute } from "@tanstack/react-router";
import { z } from "zod";
import { AssetDetailPage } from "@/features/assets/detail/asset-detail-page";
import { NotFoundPanel } from "@/features/assets/detail/not-found-panel";

export const Route = createFileRoute("/assets/$id")({
  parseParams: ({ id }) => ({ id: z.string().uuid().parse(id) }),
  component: RouteComponent,
  errorComponent: NotFoundPanel,
});

function RouteComponent() {
  const { id } = Route.useParams();
  return <AssetDetailPage id={id} />;
}
