import { Link } from "@tanstack/react-router";
import { MoreHorizontal } from "lucide-react";

import { DetailPageShell } from "@/components/layout/detail-page-shell";
import { DefinitionRow } from "@/components/ui/definition-row";
import { SectionTitle } from "@/components/ui/section-heading";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { formatDateTime } from "@/lib/date";
import type { TypeRead } from "@/features/assets/types";

import { TypeCustomFieldsDisplay } from "./type-custom-fields-display";

interface Props {
  type: TypeRead;
  onDelete: () => void;
}

export function TypeDetailView({ type, onDelete }: Props) {
  return (
    <DetailPageShell
      backLink={
        <Link
          to="/types"
          className="text-sm text-muted-foreground hover:text-foreground transition-colors"
        >
          ← 返回类型列表
        </Link>
      }
      title={type.name}
      meta={
        <span className="font-code text-sm text-muted-foreground">
          {type.code_prefix}
        </span>
      }
      actions={
        <div className="flex items-center gap-2">
          <Button variant="outline" asChild>
            <Link to="/types/$id/edit" params={{ id: type.id }}>
              编辑
            </Link>
          </Button>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon" aria-label="更多操作">
                <MoreHorizontal className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem
                onSelect={onDelete}
                className="text-destructive focus:text-destructive"
              >
                删除…
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      }
    >
      <section>
        <SectionTitle>元信息</SectionTitle>
        <dl className="divide-y divide-border/50">
          <DefinitionRow label="名称">{type.name}</DefinitionRow>
          <DefinitionRow label="代号前缀">
            <span className="font-code">{type.code_prefix}</span>
          </DefinitionRow>
          <DefinitionRow label="描述">
            {type.description || (
              <span className="text-muted-foreground">—</span>
            )}
          </DefinitionRow>
          <DefinitionRow label="资产引用数">{type.ref_count}</DefinitionRow>
          <DefinitionRow label="创建时间">
            <time className="font-code">{formatDateTime(type.created_at)}</time>
          </DefinitionRow>
          <DefinitionRow label="最后更新">
            <time className="font-code">{formatDateTime(type.updated_at)}</time>
          </DefinitionRow>
        </dl>
      </section>

      <section>
        <SectionTitle>自定义字段</SectionTitle>
        <TypeCustomFieldsDisplay fields={type.custom_fields} />
      </section>
    </DetailPageShell>
  );
}
