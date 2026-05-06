import { UserPlus } from "lucide-react";

import { EmptyCard } from "./empty-card";

export function HolderEmpty() {
  return (
    <EmptyCard
      Icon={UserPlus}
      title="还没有派发记录"
      subtitle="派发出去就有人持有了"
      cta={{ to: "/", label: "去派发" }}
    />
  );
}
