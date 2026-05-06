import { LayoutDashboard } from "lucide-react";

import { EmptyCard } from "./empty-card";

export function StatusEmpty() {
  return (
    <EmptyCard
      Icon={LayoutDashboard}
      title="还没有登记任何资产"
      subtitle="第一件资产是开始"
      cta={{ to: "/assets/new", label: "登记资产" }}
    />
  );
}
