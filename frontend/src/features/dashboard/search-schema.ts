import { z } from "zod";

export const dashboardSearchSchema = z.object({
  include_retired: z.boolean().default(false),
  include_disposed: z.boolean().default(false),
});

export type DashboardSearch = z.infer<typeof dashboardSearchSchema>;
