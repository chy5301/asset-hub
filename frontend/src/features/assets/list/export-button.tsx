import { ChevronDown, Download } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

import { searchToServerParams } from "./search-params";
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

/** spec §3.1 + §B.10: filter 透传给 /api/export, 加 format; 不传 sort/page/pageSize. */
export function buildExportUrl(
  search: AssetsSearch,
  format: "csv" | "xlsx",
): string {
  const params = new URLSearchParams({ format, ...searchToServerParams(search) });
  return `/api/export?${params.toString()}`;
}
