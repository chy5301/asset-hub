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
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import type { components } from '@/api/generated/schema';

type TypeRead = components['schemas']['TypeRead'];

interface Props {
  rows: TypeRead[];
  onDelete: (t: TypeRead) => void;
}

export function TypesTable({ rows, onDelete }: Props) {
  const columns = useMemo<ColumnDef<TypeRead>[]>(
    () => [
      {
        accessorKey: 'name',
        header: '名称',
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
        header: '代号前缀',
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
        cell: ({ row }) => (
          <Link
            to="/"
            search={{ ...ASSETS_DEFAULT_SEARCH, type: row.original.id }}
            className="text-primary hover:underline cursor-pointer"
          >
            {row.original.ref_count}
          </Link>
        ),
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
