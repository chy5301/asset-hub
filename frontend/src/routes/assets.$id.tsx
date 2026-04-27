import { createFileRoute, Outlet } from "@tanstack/react-router";
import { z } from "zod";
import { NotFoundPanel } from "@/features/assets/detail/not-found-panel";

export const Route = createFileRoute("/assets/$id")({
  parseParams: ({ id }) => ({ id: z.string().uuid().parse(id) }),
  component: () => <Outlet />,
  errorComponent: NotFoundPanel,
});
