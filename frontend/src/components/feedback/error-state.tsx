import { AlertTriangle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { toFriendlyMessage } from "@/lib/error";

interface ErrorStateProps {
  error: unknown;
  onRetry?: () => void;
}

export function ErrorState({ error, onRetry }: ErrorStateProps) {
  return (
    <div
      role="alert"
      className="flex flex-col items-center justify-center gap-3 py-16 text-center"
    >
      <AlertTriangle className="h-8 w-8 text-destructive" aria-hidden />
      <div className="space-y-1">
        <p className="text-base font-medium text-foreground">请求失败</p>
        <p className="text-sm text-muted-foreground">{toFriendlyMessage(error)}</p>
      </div>
      {onRetry ? (
        <Button variant="outline" size="sm" onClick={onRetry} className="mt-2">
          重试
        </Button>
      ) : null}
    </div>
  );
}
