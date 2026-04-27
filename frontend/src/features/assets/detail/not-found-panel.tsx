import { SearchX } from "lucide-react";
import { Link } from "@tanstack/react-router";
import { Button } from "@/components/ui/button";

export function NotFoundPanel() {
  return (
    <div
      role="alert"
      className="mx-auto flex max-w-md flex-col items-center justify-center gap-4 py-24 text-center"
    >
      <SearchX className="h-12 w-12 text-muted-foreground" aria-hidden />
      <div className="space-y-1">
        <h2 className="text-xl font-medium">资产不存在</h2>
        <p className="text-sm text-muted-foreground">
          它可能已被删除，或链接有误。
        </p>
      </div>
      <Link to="/" search={{ sort: "asset_code", page: 1, pageSize: 50 }}>
        <Button variant="outline">返回列表</Button>
      </Link>
    </div>
  );
}
