import { Component, type ErrorInfo, type ReactNode } from "react";
import { Button } from "@/components/ui/button";

interface Props {
  children: ReactNode;
}
interface State {
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    if (import.meta.env.DEV) {
      console.error("[ErrorBoundary]", error, info);
    }
  }

  handleReload = () => {
    window.location.reload();
  };

  render() {
    if (!this.state.error) return this.props.children;

    return (
      <div className="mx-auto flex max-w-md flex-col items-center gap-3 py-24 text-center">
        <p className="text-lg font-semibold">出错了</p>
        <p className="text-sm text-muted-foreground">
          {this.state.error.message || "未知异常"}
        </p>
        {import.meta.env.DEV && this.state.error.stack ? (
          <pre className="max-h-48 w-full overflow-auto rounded-md border border-border bg-muted p-3 text-left text-xs text-muted-foreground">
            {this.state.error.stack}
          </pre>
        ) : null}
        <Button variant="outline" size="sm" onClick={this.handleReload}>
          刷新页面
        </Button>
      </div>
    );
  }
}
