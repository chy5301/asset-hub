import { useMemo } from "react";
import { useNavigate } from "@tanstack/react-router";
import {
  type ColumnDef,
  flexRender,
  getCoreRowModel,
  getPaginationRowModel,
  getSortedRowModel,
  type SortingState,
  useReactTable,
} from "@tanstack/react-table";
import { ArrowDown, ArrowUp, ArrowUpDown, MoreHorizontal } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { StatusBadge } from "@/components/status/status-badge";
import type { AssetStatus } from "@/features/assets/status-labels";
import type { AssetsSearch } from "@/features/assets/list/search-schema";
import {
  COLUMN_LABELS,
  type ColumnKey,
} from "@/features/assets/list/column-visibility";

export interface AssetRow {
  id: string;
  serial_number?: string | null;
  name: string;
  type_id?: string | null;
  type_name?: string | null;
  status: AssetStatus;
  holder?: string | null;
  location?: string | null;
  updated_at: string;
}

interface AssetsTableProps {
  rows: AssetRow[];
  search: AssetsSearch;
  visible: Record<ColumnKey, boolean>;
  /** 筛选 / 排序 / 翻页变更时由父组件递增，用于触发 tbody 淡切（§3.5.5 时刻 2） */
  bodyKey: string;
}

function urlSortToState(sort?: string): SortingState {
  if (!sort) return [];
  return sort.startsWith("-")
    ? [{ id: sort.slice(1), desc: true }]
    : [{ id: sort, desc: false }];
}
function stateToUrlSort(state: SortingState): string | undefined {
  if (state.length === 0) return undefined;
  const s = state[0];
  return s.desc ? `-${s.id}` : s.id;
}

export function AssetsTable({
  rows,
  search,
  visible,
  bodyKey,
}: AssetsTableProps) {
  const navigate = useNavigate({ from: "/" });

  const sorting = useMemo(() => urlSortToState(search.sort), [search.sort]);

  const columns = useMemo<ColumnDef<AssetRow>[]>(
    () => [
      {
        id: "code",
        // 排序键：serial_number（静态识别符，缺失时回落到 id 前 8 位）
        accessorFn: (r) => r.serial_number ?? r.id.slice(0, 8),
        header: COLUMN_LABELS.code,
        cell: ({ row }) => (
          <span className="font-code text-xs">
            {row.original.serial_number ?? row.original.id.slice(0, 8)}
          </span>
        ),
      },
      {
        id: "name",
        accessorKey: "name",
        header: COLUMN_LABELS.name,
        cell: ({ row }) => (
          <span className="font-medium">{row.original.name}</span>
        ),
      },
      {
        id: "type",
        accessorKey: "type_name",
        header: COLUMN_LABELS.type,
        enableSorting: false,
        cell: ({ row }) => (
          <span className="text-sm text-muted-foreground">
            {row.original.type_name ?? "—"}
          </span>
        ),
      },
      {
        id: "status",
        accessorKey: "status",
        header: COLUMN_LABELS.status,
        enableSorting: false,
        cell: ({ row }) => <StatusBadge status={row.original.status} />,
      },
      {
        id: "holder",
        accessorKey: "holder",
        header: COLUMN_LABELS.holder,
        cell: ({ row }) => row.original.holder ?? "—",
      },
      {
        id: "location",
        accessorKey: "location",
        header: COLUMN_LABELS.location,
        cell: ({ row }) => row.original.location ?? "—",
      },
      {
        id: "updated_at",
        accessorKey: "updated_at",
        header: COLUMN_LABELS.updated_at,
        cell: ({ row }) =>
          new Date(row.original.updated_at).toLocaleString("zh-CN"),
      },
      {
        id: "actions",
        header: "",
        enableSorting: false,
        cell: ({ row }) => <RowActions id={row.original.id} />,
      },
    ],
    [],
  );

  const columnVisibility = useMemo(
    () => ({
      code: visible.code,
      name: visible.name,
      type: visible.type,
      status: visible.status,
      holder: visible.holder,
      location: visible.location,
      updated_at: visible.updated_at,
      actions: true,
    }),
    [visible],
  );

  const table = useReactTable({
    data: rows,
    columns,
    state: {
      sorting,
      columnVisibility,
      pagination: {
        pageIndex: search.page - 1,
        pageSize: search.pageSize,
      },
    },
    manualPagination: false,
    manualSorting: false,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    onSortingChange: (updater) => {
      const next = typeof updater === "function" ? updater(sorting) : updater;
      navigate({
        search: (prev) => ({
          ...prev,
          sort: stateToUrlSort(next),
          page: 1,
        }),
      });
    },
  });

  return (
    <div className="overflow-x-auto rounded-sm border border-border">
      <table className="w-full text-sm">
        <thead>
          {table.getHeaderGroups().map((hg) => (
            <tr key={hg.id} className="border-b border-border bg-muted/40 text-left">
              {hg.headers.map((header) => {
                const canSort = header.column.getCanSort();
                const sortDir = header.column.getIsSorted();
                return (
                  <th
                    key={header.id}
                    className="px-3 py-2 text-xs font-medium uppercase tracking-wide text-muted-foreground"
                  >
                    {canSort ? (
                      <button
                        type="button"
                        className="inline-flex items-center gap-1 hover:text-foreground"
                        onClick={header.column.getToggleSortingHandler()}
                      >
                        {flexRender(header.column.columnDef.header, header.getContext())}
                        {sortDir === "asc" ? (
                          <ArrowUp className="h-3 w-3" aria-hidden />
                        ) : sortDir === "desc" ? (
                          <ArrowDown className="h-3 w-3" aria-hidden />
                        ) : (
                          <ArrowUpDown className="h-3 w-3 opacity-50" aria-hidden />
                        )}
                      </button>
                    ) : (
                      flexRender(header.column.columnDef.header, header.getContext())
                    )}
                  </th>
                );
              })}
            </tr>
          ))}
        </thead>
        <tbody key={bodyKey} className="tbody-fade">
          {table.getRowModel().rows.map((row, idx) => (
            <tr
              key={row.id}
              className="stagger-row cursor-pointer border-b border-border transition-colors hover:bg-accent/40"
              style={{ animationDelay: idx < 20 ? `${idx * 18}ms` : "0ms" }}
              onClick={() =>
                navigate({ to: "/assets/$id", params: { id: row.original.id } })
              }
            >
              {row.getVisibleCells().map((cell) => (
                <td
                  key={cell.id}
                  className="px-3 py-2 align-middle"
                  onClick={(e) => {
                    if (cell.column.id === "actions") e.stopPropagation();
                  }}
                >
                  {flexRender(cell.column.columnDef.cell, cell.getContext())}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function RowActions({ id }: { id: string }) {
  // M2c-1: 菜单项全部 disabled；id 作为 data-* 留给后续接线 + 调试可见
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant="ghost"
          size="icon"
          aria-label="更多操作"
          data-asset-id={id}
        >
          <MoreHorizontal className="h-4 w-4" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        <DropdownMenuItem disabled>编辑（M2c-3 开放）</DropdownMenuItem>
        <DropdownMenuItem disabled>派发（M2c-2 开放）</DropdownMenuItem>
        <DropdownMenuItem disabled>归还（M2c-2 开放）</DropdownMenuItem>
        <DropdownMenuItem disabled>删除（M2c-3 开放）</DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
