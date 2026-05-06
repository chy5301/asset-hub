import { createFileRoute } from "@tanstack/react-router";

import { DashboardPage } from "@/features/dashboard/dashboard-page";
import { dashboardSearchSchema } from "@/features/dashboard/search-schema";

export const Route = createFileRoute("/dashboard")({
  validateSearch: (search) => dashboardSearchSchema.parse(search),
  component: DashboardPage,
});
