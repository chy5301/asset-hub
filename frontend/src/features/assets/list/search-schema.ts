import { z } from "zod";

export const ASSET_STATUS_VALUES = ["IN_USE", "IDLE", "MAINTENANCE", "RETIRED"] as const;

/** 默认排序键（升序）。后端默认按 asset_code 升序，前端 URL 同步保持一致。 */
export const DEFAULT_SORT = "asset_code";

/**
 * 资产列表路由的默认 search 对象。
 *
 * TanStack Router 在 strict typing 下要求 `Link to="/"` 显式传 search；
 * 该常量统一所有跳转入口（NavBar、AssetHeader、详情页返回链接、404 panel 等）的默认值，
 * 避免字面量在多处复制后悄悄漂移。
 */
export const ASSETS_DEFAULT_SEARCH = {
  sort: DEFAULT_SORT,
  page: 1,
  pageSize: 50,
} as const;

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
