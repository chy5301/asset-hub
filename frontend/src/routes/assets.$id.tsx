import { createFileRoute } from "@tanstack/react-router";

export const Route = createFileRoute("/assets/$id")({
  component: PlaceholderPage,
});

function PlaceholderPage() {
  return (
    <div className="py-12 text-center text-sm text-muted-foreground">
      资产详情 —— 将在 M2c-2 开放
    </div>
  );
}
