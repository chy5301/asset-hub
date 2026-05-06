/**
 * Dashboard 错误态 banner (stub).
 *
 * Task 14/15 可能再补副文案 / 视觉细化, 当前先满足 spec §3.2 retry 行为.
 */
interface Props {
  onRetry: () => void;
}

export function DashboardErrorBanner({ onRetry }: Props) {
  return (
    <div role="alert" className="rounded-md border border-destructive/40 bg-destructive/10 p-4">
      <p className="font-medium">看板加载失败</p>
      <p className="mt-1 text-sm text-muted-foreground">数据请求出错, 可重试.</p>
      <button
        type="button"
        onClick={onRetry}
        className="mt-3 text-sm underline underline-offset-4 hover:no-underline"
      >
        重试
      </button>
    </div>
  );
}
