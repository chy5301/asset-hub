import { useNavigate } from "@tanstack/react-router";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { AssetsSearch } from "@/features/assets/list/search-schema";

interface AssetsPaginationProps {
  search: AssetsSearch;
  total: number;
}

const PAGE_SIZES = [20, 50, 100, 200];

export function AssetsPagination({ search, total }: AssetsPaginationProps) {
  const navigate = useNavigate({ from: "/" });

  const totalPages = Math.max(1, Math.ceil(total / search.pageSize));
  const page = Math.min(search.page, totalPages);

  const goto = (nextPage: number) =>
    navigate({
      search: (prev) => ({
        ...prev,
        page: Math.max(1, Math.min(nextPage, totalPages)),
      }),
    });

  const changePageSize = (value: string) =>
    navigate({
      search: (prev) => ({ ...prev, pageSize: Number(value), page: 1 }),
    });

  return (
    <div className="flex items-center justify-between gap-4 text-sm">
      <div className="text-muted-foreground">
        共 <span className="font-code">{total}</span> 条 · 第{" "}
        <span className="font-code">{page}</span> /{" "}
        <span className="font-code">{totalPages}</span> 页
      </div>

      <div className="flex items-center gap-2">
        <Select value={String(search.pageSize)} onValueChange={changePageSize}>
          <SelectTrigger className="w-24" aria-label="每页条数">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {PAGE_SIZES.map((n) => (
              <SelectItem key={n} value={String(n)}>
                {n} 条/页
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Button
          variant="outline"
          size="icon"
          onClick={() => goto(page - 1)}
          disabled={page <= 1}
          aria-label="上一页"
        >
          <ChevronLeft className="h-4 w-4" />
        </Button>

        <Button
          variant="outline"
          size="icon"
          onClick={() => goto(page + 1)}
          disabled={page >= totalPages}
          aria-label="下一页"
        >
          <ChevronRight className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
}
