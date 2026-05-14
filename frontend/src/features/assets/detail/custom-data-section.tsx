import { useState } from 'react';
import { AlertTriangle, X } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { detectUnknownKeys } from '@/lib/unknown-key-detector';
import type { FieldDef } from '@/features/assets/form/types';
import { formatCustomFieldValue } from './custom-field-formatter';

interface CustomDataSectionProps {
  customData: Record<string, unknown>;
  fieldDefs: FieldDef[];
  assetId: string;
}

export function CustomDataSection({ customData, fieldDefs, assetId }: CustomDataSectionProps) {
  const report = detectUnknownKeys(customData, fieldDefs);
  const dismissKey = `unknown-fields-banner.dismissed.${assetId}`;
  const [dismissed, setDismissed] = useState(
    () => sessionStorage.getItem(dismissKey) === '1',
  );

  function handleDismiss() {
    sessionStorage.setItem(dismissKey, '1');
    setDismissed(true);
  }

  const declaredEntries = fieldDefs.map((f) => ({
    def: f,
    value: customData[f.key],
  }));
  const orphanEntries = report.orphanKeys.map((k) => ({
    key: k,
    value: customData[k],
  }));

  // 没有任何字段可展示且无 banner 触发 → 隐藏整个 section（与 old custom-fields.tsx 行为一致）
  if (declaredEntries.length === 0 && orphanEntries.length === 0 && !report.hasIssues) {
    return null;
  }

  return (
    <section className="space-y-4">
      <h2 className="mb-3 text-lg font-medium">类型字段</h2>
      {!dismissed && report.hasIssues && (
        <div
          role="alert"
          className="flex items-start gap-3 rounded border border-warning/30 bg-warning/10 p-3 text-sm"
        >
          <AlertTriangle className="h-4 w-4 shrink-0 mt-0.5 text-warning" />
          <div className="flex-1 space-y-1">
            <p className="font-medium text-warning">
              该资产含 {report.orphanKeys.length} 个未声明字段 / {report.violatedRequired.length} 个必填项为空
            </p>
            <ul className="text-xs text-foreground space-y-0.5">
              {report.orphanKeys.map((k) => (
                <li key={k}>未声明字段：<span className="font-mono">{k}</span></li>
              ))}
              {report.violatedRequired.map(({ key }) => (
                <li key={key}>必填项为空：<span className="font-mono">{key}</span></li>
              ))}
            </ul>
          </div>
          <button
            type="button"
            onClick={handleDismiss}
            aria-label="关闭提示"
            className="text-muted-foreground hover:text-foreground cursor-pointer"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      )}

      <dl className="space-y-3">
        {declaredEntries.map(({ def, value }) => (
          <div key={def.key}>
            <dt className="text-xs uppercase text-muted-foreground">
              {def.label ?? def.key}
              {def.required && <span className="ml-1 text-destructive">*</span>}
            </dt>
            <dd>{formatCustomFieldValue(def, value)}</dd>
          </div>
        ))}
        {orphanEntries.map(({ key, value }) => (
          <div key={key} className="text-muted-foreground">
            <dt className="text-xs uppercase">
              {key}
              <Badge variant="outline" className="ml-2 text-xs">未声明</Badge>
            </dt>
            <dd>{String(value ?? '—')}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}
