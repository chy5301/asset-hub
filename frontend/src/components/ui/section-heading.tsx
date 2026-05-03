import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

interface Props {
  children: ReactNode;
  className?: string;
}

/** 详情阅读区 section 标题（GeneralFields / AttachmentGrid / CheckoutTimeline 风格）。 */
export function SectionTitle({ children, className }: Props) {
  return (
    <h2 className={cn("mb-3 text-lg font-medium", className)}>{children}</h2>
  );
}

/** 表单 / 元信息密度区 section caption。
 *  CJK 字符上 `text-transform: uppercase` 无效，留给英文场景生效；中文渲染不变。 */
export function SectionCaption({ children, className }: Props) {
  return (
    <h2
      className={cn(
        "text-sm font-semibold uppercase tracking-wide text-foreground border-b pb-1.5",
        className,
      )}
    >
      {children}
    </h2>
  );
}
