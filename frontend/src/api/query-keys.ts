import type { AssetsSearch } from "@/features/assets/list/search-schema";

export const qk = {
  assets: {
    all: ["assets"] as const,
    list: (params: AssetsSearch) => ["assets", "list", params] as const,
    detail: (id: string) => ["assets", "detail", id] as const,
  },
  assetTypes: {
    all: ["assetTypes"] as const,
    list: () => ["assetTypes", "list"] as const,
  },
} as const;
