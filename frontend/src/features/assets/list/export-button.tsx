import { ChevronDown, Download } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

import type { AssetsSearch } from "./search-schema";

interface ExportButtonProps {
  search: AssetsSearch;
}

/**
 * 列表页"导出 ▾" DropdownMenu (spec §3 / §B.8 决议 A).
 *
 * 用 <DropdownMenuItem asChild><a href download> 让浏览器原生触发下载;
 * 不走 fetch/blob (代码最简, 浏览器 native 下载状态/错误 UI 已足够).
 */
export function ExportButton({ search }: ExportButtonProps) {
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="outline" size="sm" aria-label="导出">
          <Download className="mr-2 h-4 w-4" />
          <span>导出</span>
          <ChevronDown className="ml-2 h-4 w-4" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        <DropdownMenuItem asChild>
          <a href={buildExportUrl(search, "xlsx")} download>
            Excel
          </a>
        </DropdownMenuItem>
        <DropdownMenuItem asChild>
          <a href={buildExportUrl(search, "csv")} download>
            CSV
          </a>
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

/**
 * spec §3.1: 把 AssetsSearch 翻译为 /api/export query string.
 *
 * - 仅传 filter 字段 (type/status/holder/q/show_retired/show_disposed)
 * - 不传 sort/page/pageSize (v1 export 整 filter 集, 不分页 - spec §B.10)
 * - 字段名翻译: show_retired → include_retired (与后端 list/stats 一致)
 */
export function buildExportUrl(
  search: AssetsSearch,
  format: "csv" | "xlsx",
): string {
  const params = new URLSearchParams({ format });
  if (search.type) params.set("type_id", search.type);
  if (search.status) params.set("status", search.status);
  if (search.holder) params.set("holder", search.holder);
  if (search.q) params.set("q", search.q);
  if (search.show_retired) params.set("include_retired", "true");
  if (search.show_disposed) params.set("include_disposed", "true");
  return `/api/export?${params.toString()}`;
}
