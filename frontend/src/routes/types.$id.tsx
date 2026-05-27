import { createFileRoute, Outlet } from "@tanstack/react-router";
import { z } from "zod";
import { TypeNotFound } from "@/features/types/detail/type-not-found";

export const Route = createFileRoute("/types/$id")({
  parseParams: ({ id }) => ({ id: z.string().uuid().parse(id) }),
  component: () => <Outlet />,
  errorComponent: TypeNotFound,
});
