import { CopyableText } from "@/components/copyable-text";
import { formatDateTime } from "@/lib/date";
import type { AssetRead } from "@/features/assets/types";
import { DefinitionRow } from "./definition-row";

interface GeneralFieldsProps {
  asset: AssetRead;
  typeName: string | undefined;
}

export function GeneralFields({ asset, typeName }: GeneralFieldsProps) {
  return (
    <section>
      <h2 className="mb-3 text-lg font-medium">通用字段</h2>
      <dl className="divide-y divide-border/50">
        <DefinitionRow label="编号（SN）">
          {asset.serial_number ? (
            <CopyableText value={asset.serial_number} toastLabel="编号" />
          ) : (
            <span className="text-muted-foreground">—</span>
          )}
        </DefinitionRow>
        <DefinitionRow label="资产 ID">
          <CopyableText value={asset.id} toastLabel="资产 ID" />
        </DefinitionRow>
        <DefinitionRow label="类型">{typeName ?? "—"}</DefinitionRow>
        <DefinitionRow label="当前持有人">{asset.holder ?? "—"}</DefinitionRow>
        <DefinitionRow label="当前位置">{asset.location ?? "—"}</DefinitionRow>
        <DefinitionRow label="备注">
          <span className="whitespace-pre-wrap">{asset.notes ?? "—"}</span>
        </DefinitionRow>
        <DefinitionRow label="创建时间">
          <time className="font-code">{formatDateTime(asset.created_at)}</time>
        </DefinitionRow>
        <DefinitionRow label="最后更新">
          <time className="font-code">{formatDateTime(asset.updated_at)}</time>
        </DefinitionRow>
      </dl>
    </section>
  );
}
