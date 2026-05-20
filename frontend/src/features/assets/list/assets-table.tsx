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
import { formatDateTime } from "@/lib/date";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { StatusBadge } from "@/components/status/status-badge";
import type { AssetStatus } from "@/features/assets/status-labels";
import { type AssetsSearch, DEFAULT_SORT } from "@/features/assets/list/search-schema";
import {
  COLUMN_LABELS,
  type ColumnKey,
} from "@/features/assets/list/column-visibility";
import type { CheckoutKind } from "@/features/assets/detail/available-transitions";

export interface AssetRow {
  id: string;
  asset_code: string;
  serial_number?: string | null;
  name: string;
  brand?: string | null;
  model?: string | null;
  type_id?: string | null;
  type_name?: string | null;
  status: AssetStatus;
  holder?: string | null;
  location?: string | null;
  updated_at: string;
  acquired_at?: string | null;
  current_checkout_id?: string | null;
}

interface AssetsTableProps {
  rows: AssetRow[];
  search: AssetsSearch;
  visible: Record<ColumnKey, boolean>;
  /** 筛选 / 排序 / 翻页变更时由父组件递增，用于触发 tbody 淡切（§3.5.5 时刻 2） */
  bodyKey: string;
  onCheckout: (row: AssetRow, kind: CheckoutKind) => void;
  onReturn: (row: AssetRow) => void;
  onDelete: (row: AssetRow) => void;
}

function urlSortToState(sort?: string): SortingState {
  if (!sort) return [];
  return sort.startsWith("-")
    ? [{ id: sort.slice(1), desc: true }]
    : [{ id: sort, desc: false }];
}
function stateToUrlSort(state: SortingState): string {
  if (state.length === 0) return DEFAULT_SORT;
  const s = state[0];
  return s.desc ? `-${s.id}` : s.id;
}

export function AssetsTable({
  rows,
  search,
  visible,
  bodyKey,
  onCheckout,
  onReturn,
  onDelete,
}: AssetsTableProps) {
  const navigate = useNavigate({ from: "/" });

  const sorting = useMemo(() => urlSortToState(search.sort), [search.sort]);

  const columns = useMemo<ColumnDef<AssetRow>[]>(
    () => [
      {
        id: "asset_code",
        accessorKey: "asset_code",
        header: COLUMN_LABELS.asset_code,
        cell: ({ row }) => (
          <span className="font-code text-xs">{row.original.asset_code}</span>
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
        id: "brand",
        accessorKey: "brand",
        header: COLUMN_LABELS.brand,
        cell: ({ row }) =>
          row.original.brand ?? (
            <span className="text-muted-foreground">—</span>
          ),
      },
      {
        id: "model",
        accessorKey: "model",
        header: COLUMN_LABELS.model,
        cell: ({ row }) =>
          row.original.model ?? (
            <span className="text-muted-foreground">—</span>
          ),
      },
      {
        id: "serial_number",
        accessorKey: "serial_number",
        header: COLUMN_LABELS.serial_number,
        cell: ({ row }) =>
          row.original.serial_number ? (
            <span className="font-code text-xs">{row.original.serial_number}</span>
          ) : (
            <span className="text-muted-foreground">—</span>
          ),
      },
      {
        id: "type",
        accessorFn: (r) => r.type_name ?? "",
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
        cell: ({ row }) => formatDateTime(row.original.updated_at),
      },
      {
        id: "acquired_at",
        accessorKey: "acquired_at",
        header: COLUMN_LABELS.acquired_at,
        cell: ({ row }) =>
          row.original.acquired_at ? (
            <span className="font-code text-xs">{row.original.acquired_at}</span>
          ) : (
            <span className="text-muted-foreground">—</span>
          ),
      },
      {
        id: "actions",
        header: "",
        enableSorting: false,
        cell: ({ row }) => (
          <RowActions
            row={row.original}
            onCheckout={onCheckout}
            onReturn={onReturn}
            onDelete={onDelete}
          />
        ),
      },
    ],
    [onCheckout, onReturn, onDelete],
  );

  const columnVisibility = useMemo(
    () => ({ ...visible, actions: true as const }),
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

function RowActions({
  row,
  onCheckout,
  onReturn,
  onDelete,
}: {
  row: AssetRow;
  onCheckout: (row: AssetRow, kind: CheckoutKind) => void;
  onReturn: (row: AssetRow) => void;
  onDelete: (row: AssetRow) => void;
}) {
  const navigate = useNavigate();
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant="ghost"
          size="icon"
          aria-label="更多操作"
          data-asset-id={row.id}
        >
          <MoreHorizontal className="h-4 w-4" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent
        align="end"
        // Radix Portal 渲染：菜单项点击仍沿 React 父链冒泡到 <tr onClick>，
        // 否则点「编辑」会同时触发行点击导航到详情页
        onClick={(e) => e.stopPropagation()}
      >
        <DropdownMenuItem
          onSelect={() =>
            navigate({ to: "/assets/$id/edit", params: { id: row.id } })
          }
        >
          编辑
        </DropdownMenuItem>
        <DropdownMenuItem
          onSelect={() => onCheckout(row, "CHECKOUT_INTERNAL")}
          disabled={row.status !== "IDLE"}
        >
          派发
        </DropdownMenuItem>
        <DropdownMenuItem
          onSelect={() => onCheckout(row, "CHECKOUT_EXTERNAL")}
          disabled={row.status !== "IDLE"}
        >
          出借
        </DropdownMenuItem>
        <DropdownMenuItem
          onSelect={() => onReturn(row)}
          disabled={row.status !== "IN_USE"}
        >
          归还
        </DropdownMenuItem>
        <DropdownMenuSeparator />
        <DropdownMenuItem
          onSelect={() => onDelete(row)}
          disabled={row.status === "IN_USE"}
          className="text-destructive focus:text-destructive"
        >
          删除…
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
