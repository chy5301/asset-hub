import { z } from "zod";

export const ASSET_STATUS_VALUES = ["IN_USE", "IDLE", "MAINTENANCE", "RETIRED"] as const;

/** 默认排序键（升序）。后端默认按 asset_code 升序，前端 URL 同步保持一致。 */
export const DEFAULT_SORT = "asset_code";

export const assetsSearchSchema = z.object({
  type: z.string().uuid().optional(),
  status: z.enum(ASSET_STATUS_VALUES).optional(),
  holder: z.string().optional(),
  q: z.string().optional(),
  sort: z.string().optional().default(DEFAULT_SORT),
  page: z.coerce.number().int().min(1).default(1),
  pageSize: z.coerce.number().int().min(10).max(200).default(50),
});

export type AssetsSearch = z.infer<typeof assetsSearchSchema>;
