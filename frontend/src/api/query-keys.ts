type AssetListParams = Record<string, unknown>;

export const qk = {
  assets: {
    all: ["assets"] as const,
    list: (params: AssetListParams) => ["assets", "list", params] as const,
    detail: (id: string) => ["assets", "detail", id] as const,
  },
  assetTypes: {
    all: ["assetTypes"] as const,
    list: () => ["assetTypes", "list"] as const,
  },
} as const;
