import { createFileRoute, Outlet } from "@tanstack/react-router";
import { z } from "zod";
import { AssetNotFound } from "@/features/assets/detail/asset-not-found";

export const Route = createFileRoute("/assets/$id")({
  parseParams: ({ id }) => ({ id: z.string().uuid().parse(id) }),
  component: () => <Outlet />,
  errorComponent: AssetNotFound,
});
