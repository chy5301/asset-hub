import { createFileRoute } from "@tanstack/react-router";

export const Route = createFileRoute("/")({
  component: IndexPage,
});

function IndexPage() {
  return (
    <div>
      <h2 className="text-lg font-medium">资产列表</h2>
      <p className="mt-2 text-muted-foreground">M2 实现</p>
    </div>
  );
}
