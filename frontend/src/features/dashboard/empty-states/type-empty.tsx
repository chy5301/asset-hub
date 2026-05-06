import { Boxes } from "lucide-react";

import { EmptyCard } from "./empty-card";

export function TypeEmpty() {
  return (
    <EmptyCard
      Icon={Boxes}
      title="尚未定义任何类型"
      subtitle="先建一个类型再开始登记"
      cta={{ to: "/types", label: "管理类型" }}
    />
  );
}
