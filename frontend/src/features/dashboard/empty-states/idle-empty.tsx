import { Leaf } from "lucide-react";

import { EmptyCard } from "./empty-card";

export function IdleEmpty() {
  return (
    <EmptyCard
      Icon={Leaf}
      title="没有闲置资产"
      subtitle="一切都在用——干得不错"
    />
  );
}
