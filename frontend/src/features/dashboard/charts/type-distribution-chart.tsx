/**
 * 类型分布 donut (stub).
 *
 * Task 12 替换为 Recharts PieChart (innerRadius) + 类型色板.
 */
import type { TypeDistributionItem } from "@/features/assets/types";

interface Props {
  data: TypeDistributionItem[];
}

export function TypeDistributionChart({ data }: Props) {
  return (
    <section className="rounded-lg border bg-card p-6">
      <h2 className="text-base font-medium">类型分布</h2>
      <p className="mt-2 text-sm text-muted-foreground">{data.length} 条 (Task 12 实装)</p>
    </section>
  );
}
