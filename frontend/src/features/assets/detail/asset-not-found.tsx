import { Link } from "@tanstack/react-router";
import { Button } from "@/components/ui/button";
import { NotFoundPanel } from "@/components/feedback/not-found-panel";
import { ASSETS_DEFAULT_SEARCH } from "@/features/assets/list/search-schema";

export function AssetNotFound() {
  return (
    <NotFoundPanel
      title="资产不存在"
      description="它可能已被删除，或链接有误。"
      backLink={
        <Link to="/" search={ASSETS_DEFAULT_SEARCH}>
          <Button variant="outline">返回列表</Button>
        </Link>
      }
    />
  );
}
