import type { AssetsSearch } from "@/features/assets/list/search-schema";

export const qk = {
  assets: {
    all: ["assets"] as const,
    list: (params: AssetsSearch) => ["assets", "list", params] as const,
    detail: (id: string) => ["assets", "detail", id] as const,
    // asymmetric shape intentional: transitions 嵌在 qk.assets 下，让 qk.assets.all
    // 失效（e.g. transition 成功后）自动级联失效本 key。spec §5.7
    transitions: (id: string) => ["assets", id, "transitions"] as const,
  },
  assetTypes: {
    all: ["assetTypes"] as const,
    list: () => ["assetTypes", "list"] as const,
    detail: (id: string) => ["assetTypes", "detail", id] as const,
  },
  attachments: {
    byAsset: (assetId: string) =>
      ["attachments", "byAsset", assetId] as const,
  },
} as const;
