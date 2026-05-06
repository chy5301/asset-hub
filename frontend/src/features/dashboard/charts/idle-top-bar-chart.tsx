/**
 * 闲置时长 Top 10 横向条 (stub).
 *
 * Task 12 替换为 Recharts 横向 BarChart + 状态色 token.
 */
import type { IdleTopItem } from "@/features/assets/types";

interface Props {
  data: IdleTopItem[];
}

export function IdleTopBarChart({ data }: Props) {
  return (
    <section className="rounded-lg border bg-card p-6">
      <h2 className="text-base font-medium">闲置时长 Top 10</h2>
      <p className="mt-2 text-sm text-muted-foreground">{data.length} 条数据 (Task 12 实装)</p>
    </section>
  );
}
