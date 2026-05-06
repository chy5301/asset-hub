/**
 * 业务 DTO alias 层 (spec §D1 决议).
 *
 * 全前端业务代码 import 业务类型只走此文件, 不再直接 import generated schema.
 * 未来 codegen 工具切换 / 后端 DTO 改名 → 仅改此文件, 业务代码 0 churn.
 *
 * 此文件与 api/types.ts (spec §H4) 关注点分离:
 * - api/types.ts = API 客户端通用包装 (OpenapiFetchResult/unwrap)
 * - 此文件 = 业务 DTO 重命名导出
 */
import type { components } from "@/api/generated/schema";

type S = components["schemas"];

// === Asset ===
export type AssetRead = S["AssetRead"];
export type AssetCreate = S["AssetCreate"];
export type AssetUpdate = S["AssetUpdate"];
export type AssetStatus = S["AssetStatus"];

// === Type (asset type 定义) ===
export type TypeRead = S["TypeRead"];
export type TypeCreate = S["TypeCreate"];
export type TypeUpdate = S["TypeUpdate"];
export type CustomFieldDef = S["CustomFieldDef"];

// === Transition ===
export type TransitionRead = S["TransitionRead"];
export type TransitionCreate = S["TransitionCreate"];
export type TransitionKind = S["TransitionKind"];

// === Attachment ===
export type AttachmentRead = S["AttachmentRead"];

// === Stats (M3b 新) ===
export type StatsRead = S["StatsRead"];
export type StatsSummary = S["StatsSummary"];
export type IdleTopItem = S["IdleTopItem"];
export type HolderRankingItem = S["HolderRankingItem"];
export type TypeDistributionItem = S["TypeDistributionItem"];
