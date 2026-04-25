interface InlineErrorBannerProps {
  message: string;
}

export function InlineErrorBanner({ message }: InlineErrorBannerProps) {
  return (
    <div
      role="alert"
      className="rounded-sm border border-destructive/50 bg-destructive/10 px-3 py-2 text-sm text-destructive"
    >
      {message}
    </div>
  );
}
