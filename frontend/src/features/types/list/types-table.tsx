import { Link } from '@tanstack/react-router';
import { useMemo } from 'react';
import { ASSETS_DEFAULT_SEARCH } from '@/features/assets/list/search-schema';
import {
  flexRender,
  getCoreRowModel,
  useReactTable,
  type ColumnDef,
} from '@tanstack/react-table';
import { MoreHorizontal } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { useAssetsQuery } from '@/api/hooks/assets';
import type { components } from '@/api/generated/schema';

type TypeRead = components['schemas']['TypeRead'];

function RefCountCell({ typeId }: { typeId: string }) {
  // pageSize 200：toServerParams 不发往后端，服务端总返完整 type 过滤列表，但 zod schema 要求 ≥10。
  // M3 排期建议后端在 TypeRead 暴露 ref_count 消除此处 N+1 + 列表上限隐患（PR-3 final review followup）。
  const q = useAssetsQuery({ type: typeId, page: 1, pageSize: 200, sort: 'asset_code' });
  if (q.isLoading) return <Skeleton className="inline-block h-3 w-6" />;
  const total = q.data?.length ?? 0;
  return (
    <Link
      to="/"
      search={{ ...ASSETS_DEFAULT_SEARCH, type: typeId }}
      className="text-primary hover:underline cursor-pointer"
    >
      {total}
    </Link>
  );
}

interface Props {
  rows: TypeRead[];
  onDelete: (t: TypeRead) => void;
}

export function TypesTable({ rows, onDelete }: Props) {
  const columns = useMemo<ColumnDef<TypeRead>[]>(
    () => [
      {
        accessorKey: 'name',
        header: 'name',
        cell: ({ row }) => (
          <Link
            to="/types/$id"
            params={{ id: row.original.id }}
            className="font-medium hover:underline cursor-pointer"
          >
            {row.original.name}
          </Link>
        ),
      },
      {
        accessorKey: 'code_prefix',
        header: 'code_prefix',
        cell: ({ row }) => (
          <span className="font-mono text-xs">{row.original.code_prefix}</span>
        ),
      },
      {
        id: 'fieldCount',
        header: '字段数',
        cell: ({ row }) => (
          <Badge variant="secondary">
            {row.original.custom_fields?.length ?? 0} 个字段
          </Badge>
        ),
      },
      {
        id: 'refCount',
        header: '资产引用',
        cell: ({ row }) => <RefCountCell typeId={row.original.id} />,
      },
      {
        id: 'actions',
        header: '',
        cell: ({ row }) => (
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon" aria-label="更多操作">
                <MoreHorizontal className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="bg-popover">
              <DropdownMenuItem
                onSelect={() => onDelete(row.original)}
                className="text-destructive focus:text-destructive cursor-pointer"
              >
                删除…
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        ),
      },
    ],
    [onDelete],
  );

  const table = useReactTable({
    data: rows,
    columns,
    getCoreRowModel: getCoreRowModel(),
  });

  return (
    // rounded-sm / hover:bg-accent/40 与 assets-table 保持一致（source of truth）
    <div className="overflow-x-auto rounded-sm border border-border">
      <table className="w-full text-sm">
        <thead>
          {table.getHeaderGroups().map((hg) => (
            <tr
              key={hg.id}
              className="border-b border-border bg-muted/40 text-left"
            >
              {hg.headers.map((h) => (
                <th
                  key={h.id}
                  className="px-3 py-2 text-xs font-medium uppercase tracking-wide text-muted-foreground"
                >
                  {flexRender(h.column.columnDef.header, h.getContext())}
                </th>
              ))}
            </tr>
          ))}
        </thead>
        <tbody>
          {table.getRowModel().rows.map((row) => (
            <tr
              key={row.id}
              className="border-b border-border last:border-b-0 transition-colors hover:bg-accent/40"
            >
              {row.getVisibleCells().map((cell) => (
                <td key={cell.id} className="px-3 py-2 align-middle">
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
