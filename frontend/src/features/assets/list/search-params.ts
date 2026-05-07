import type { AssetsSearch } from "./search-schema";

/**
 * 把 AssetsSearch 翻译为后端 server params.
 *
 * - 字段名映射: type → type_id, show_retired → include_retired,
 *   show_disposed → include_disposed (与后端 list/stats/export 一致)
 * - 仅传 filter 字段, 排除 sort/page/pageSize (这些是客户端语义)
 * - falsy 值 (undefined / false / "") 不发参, 让后端 default 兜底
 */
export function searchToServerParams(search: AssetsSearch): Record<string, string> {
  const params: Record<string, string> = {};
  if (search.type) params.type_id = search.type;
  if (search.status) params.status = search.status;
  if (search.holder) params.holder = search.holder;
  if (search.q) params.q = search.q;
  if (search.show_retired) params.include_retired = "true";
  if (search.show_disposed) params.include_disposed = "true";
  return params;
}
