export type COLUMN_KEY =
  | "asset_code"
  | "name"
  | "type"
  | "status"
  | "holder"
  | "location"
  | "updated_at";

export const COLUMN_LABELS: Record<COLUMN_KEY, string> = {
  asset_code: "编号",
  name: "名称",
  type: "类型",
  status: "状态",
  holder: "保管人",
  location: "位置",
  updated_at: "更新时间",
};

export const STORAGE_KEY = "asset-hub.list.columns";
export const ALL_KEYS: COLUMN_KEY[] = [
  "asset_code",
  "name",
  "type",
  "status",
  "holder",
  "location",
  "updated_at",
];
