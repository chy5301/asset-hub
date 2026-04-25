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
          <span className="font-code">{asset.serial_number ?? "—"}</span>
        </Row>
        <Row label="资产 ID">
          <CopyableId id={asset.id} />
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

function CopyableId({ id }: { id: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <span className="inline-flex items-center gap-2">
      <span className="font-code">{id}</span>
      <Button
        variant="ghost"
        size="icon"
        className="h-6 w-6"
        aria-label="复制资产 ID"
        onClick={async () => {
          await navigator.clipboard.writeText(id);
          setCopied(true);
          toast.success("资产 ID 已复制");
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
