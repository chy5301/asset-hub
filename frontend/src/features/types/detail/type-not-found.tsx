import { Link } from "@tanstack/react-router";
import { Button } from "@/components/ui/button";
import { NotFoundPanel } from "@/components/feedback/not-found-panel";

export function TypeNotFound() {
  return (
    <NotFoundPanel
      title="该类型不存在"
      description="可能已被删除，或链接有误。"
      backLink={
        <Button asChild variant="outline">
          <Link to="/types">返回类型列表</Link>
        </Button>
      }
    />
  );
}
