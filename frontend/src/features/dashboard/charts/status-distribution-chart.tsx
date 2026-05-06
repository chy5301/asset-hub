/**
 * 状态分布 stacked bar (stub).
 *
 * Task 13 替换为单行水平 stacked bar (status token 映射).
 */
interface Props {
  data: Record<string, number> | null;
}

export function StatusDistributionChart({ data }: Props) {
  const total = Object.values(data ?? {}).reduce((sum, c) => sum + c, 0);
  return (
    <section className="rounded-lg border bg-card p-6">
      <h2 className="text-base font-medium">状态分布</h2>
      <p className="mt-2 text-sm text-muted-foreground">总 {total} (Task 13 实装)</p>
    </section>
  );
}
