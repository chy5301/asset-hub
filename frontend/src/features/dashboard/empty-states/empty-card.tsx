import { Link } from "@tanstack/react-router";
import { type LucideIcon } from "lucide-react";

import { Button } from "@/components/ui/button";

interface EmptyCardProps {
  Icon: LucideIcon;
  title: string;
  subtitle: string;
  cta?: { to: string; label: string };
}

/**
 * 4 个差异化空态共用容器 (spec §3.7).
 * Icon 容器 (size-12 + ring + muted bg) + 标题 + italic 副标 + 可选 outline CTA.
 */
export function EmptyCard({ Icon, title, subtitle, cta }: EmptyCardProps) {
  return (
    <section className="rounded-lg border bg-card p-6 flex flex-col items-center justify-center gap-3 min-h-[200px] text-center">
      <div className="size-12 rounded-full bg-muted/50 ring-1 ring-border/50 flex items-center justify-center">
        <Icon className="size-[18px] text-muted-foreground" />
      </div>
      <div className="space-y-1">
        <h3 className="text-base font-medium">{title}</h3>
        <p className="text-sm text-muted-foreground italic">{subtitle}</p>
      </div>
      {cta && (
        <Button asChild variant="outline" size="sm">
          <Link to={cta.to}>{cta.label}</Link>
        </Button>
      )}
    </section>
  );
}
