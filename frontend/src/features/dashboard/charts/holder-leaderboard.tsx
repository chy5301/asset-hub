/**
 * 保管人持有列表 (stub).
 *
 * Task 13 替换为带头像/序号的排行榜列表.
 */
import type { HolderRankingItem } from "@/features/assets/types";

interface Props {
  data: HolderRankingItem[];
}

export function HolderLeaderboard({ data }: Props) {
  return (
    <section className="rounded-lg border bg-card p-6">
      <h2 className="text-base font-medium">保管人持有</h2>
      <p className="mt-2 text-sm text-muted-foreground">{data.length} 名 (Task 13 实装)</p>
    </section>
  );
}
