import type { LucideIcon } from "lucide-react";
import { SearchX } from "lucide-react";
import type { ReactNode } from "react";

interface NotFoundPanelProps {
  icon?: LucideIcon;
  title: string;
  description?: string;
  backLink: ReactNode;
}

export function NotFoundPanel({
  icon: Icon = SearchX,
  title,
  description,
  backLink,
}: NotFoundPanelProps) {
  return (
    <div
      role="status"
      className="mx-auto flex max-w-md flex-col items-center justify-center gap-4 py-24 text-center"
    >
      <Icon className="h-12 w-12 text-muted-foreground" aria-hidden />
      <div className="space-y-1">
        <h2 className="text-xl font-medium">{title}</h2>
        {description ? (
          <p className="text-sm text-muted-foreground">{description}</p>
        ) : null}
      </div>
      <div>{backLink}</div>
    </div>
  );
}
