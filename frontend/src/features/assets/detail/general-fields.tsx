// frontend/src/features/assets/detail/general-fields.tsx
import { useState } from "react";
import { format, parseISO } from "date-fns";
import { Copy, Check } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import type { components } from "@/api/generated/schema";

type AssetRead = components["schemas"]["AssetRead"];

interface GeneralFieldsProps {
  asset: AssetRead;
  typeName: string | undefined;
}

export function GeneralFields({ asset, typeName }: GeneralFieldsProps) {
  return (
    <section>
      <h2 className="mb-3 text-lg font-medium">通用字段</h2>
      <dl className="divide-y divide-border/50">
        <Row label="编号（SN）">
          {asset.serial_number ? (
            <CopyableText value={asset.serial_number} toastLabel="编号" />
          ) : (
            <span className="text-muted-foreground">—</span>
          )}
        </Row>
        <Row label="资产 ID">
          <CopyableText value={asset.id} toastLabel="资产 ID" />
        </Row>
        <Row label="类型">{typeName ?? "—"}</Row>
        <Row label="当前持有人">{asset.holder ?? "—"}</Row>
        <Row label="当前位置">{asset.location ?? "—"}</Row>
        <Row label="备注">
          <span className="whitespace-pre-wrap">{asset.notes ?? "—"}</span>
        </Row>
        <Row label="创建时间">
          <time className="font-code">
            {format(parseISO(asset.created_at), "yyyy-MM-dd HH:mm")}
          </time>
        </Row>
        <Row label="最后更新">
          <time className="font-code">
            {format(parseISO(asset.updated_at), "yyyy-MM-dd HH:mm")}
          </time>
        </Row>
      </dl>
    </section>
  );
}

function Row({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div className="grid grid-cols-[10rem_1fr] gap-4 py-3 text-sm">
      <dt className="text-muted-foreground">{label}</dt>
      <dd>{children}</dd>
    </div>
  );
}

/**
 * 标识符类长字符串字段的复制 UI（SN / 资产 ID / 未来 asset_code 等）。
 * - value 等宽渲染（font-code）
 * - 右侧 ghost icon 按钮，点击 navigator.clipboard.writeText(value) + toast
 * - 复制成功后 1500ms 内 icon 暂态切换为 Check 反馈
 */
function CopyableText({
  value,
  toastLabel,
}: {
  value: string;
  toastLabel: string;
}) {
  const [copied, setCopied] = useState(false);
  return (
    <span className="inline-flex items-center gap-2">
      <span className="font-code">{value}</span>
      <Button
        variant="ghost"
        size="icon"
        className="h-6 w-6"
        aria-label={`复制${toastLabel}`}
        onClick={async () => {
          await navigator.clipboard.writeText(value);
          setCopied(true);
          toast.success(`${toastLabel}已复制`);
          setTimeout(() => setCopied(false), 1500);
        }}
      >
        {copied ? (
          <Check className="h-3 w-3" />
        ) : (
          <Copy className="h-3 w-3" />
        )}
      </Button>
    </span>
  );
}
