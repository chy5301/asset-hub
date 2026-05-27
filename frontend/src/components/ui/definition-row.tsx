import type { ReactNode } from "react";

interface DefinitionRowProps {
  label: ReactNode;
  children: ReactNode;
}

/** 详情页通用 dt/dd 行：左 10rem 标签 + 右内容。 */
export function DefinitionRow({ label, children }: DefinitionRowProps) {
  return (
    <div className="grid grid-cols-[10rem_1fr] gap-4 py-3 text-sm">
      <dt className="text-muted-foreground">{label}</dt>
      <dd>{children}</dd>
    </div>
  );
}
