import { type AssetStatus, STATUS_META } from "@/features/assets/status-labels";

interface Props {
  data: Record<string, number> | null;
}

const ORDER: AssetStatus[] = ["IDLE", "IN_USE", "MAINTENANCE", "RETIRED", "DISPOSED"];
const SEGMENT_LABEL_MIN_PCT = 6;

export function StatusDistributionChart({ data }: Props) {
  const safeData = data ?? {};
  const entries = ORDER
    .map((status) => ({ status, count: safeData[status] ?? 0 }))
    .filter((e) => e.count > 0);
  const total = entries.reduce((sum, e) => sum + e.count, 0);

  if (total === 0) {
    return (
      <section className="rounded-lg border bg-card p-6 flex items-center justify-center min-h-[200px]">
        <p className="text-sm text-muted-foreground italic">还没有登记任何资产</p>
      </section>
    );
  }

  return (
    <section className="rounded-lg border bg-card p-6 flex flex-col">
      <h2 className="text-base font-medium mb-4">状态分布</h2>

      {/* 单条 stacked bar + segment 内联数字 (spec §3.3 三层信号 ①) */}
      <div className="flex h-9 rounded-md overflow-hidden">
        {entries.map((e) => {
          const meta = STATUS_META[e.status];
          const pct = (e.count / total) * 100;
          return (
            <div
              key={e.status}
              className="flex items-center justify-center text-xs font-medium"
              style={{
                width: `${pct}%`,
                background: `var(${meta.bgVar})`,
                color: `var(${meta.fgVar})`,
                borderRight: "1px solid var(--background)",
              }}
              title={`${meta.label} ${e.count}`}
            >
              {pct >= SEGMENT_LABEL_MIN_PCT && <span>{e.count}</span>}
            </div>
          );
        })}
      </div>

      {/* dot legend (spec §3.3 三层信号 ②) */}
      <ul className="flex flex-wrap gap-3 mt-3 text-xs">
        {entries.map((e) => {
          const meta = STATUS_META[e.status];
          return (
            <li key={e.status} className="flex items-center gap-1.5">
              <span
                className="size-2 rounded-sm"
                style={{ background: `var(${meta.bgVar})` }}
              />
              <span className="text-muted-foreground">{meta.label}</span>
              <span className="tabular-nums">{e.count}</span>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
