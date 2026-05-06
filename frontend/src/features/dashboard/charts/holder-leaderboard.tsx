import type { HolderRankingItem } from "@/features/assets/types";

import { HolderEmpty } from "../empty-states/holder-empty";

interface Props {
  data: HolderRankingItem[];
}

export function HolderLeaderboard({ data }: Props) {
  if (data.length === 0) return <HolderEmpty />;

  const max = data[0]?.count ?? 0;

  return (
    <section className="rounded-lg border bg-card p-6 flex flex-col">
      <h2 className="text-base font-medium mb-4">保管人持有</h2>
      <ul className="flex-1 max-h-72 overflow-y-auto space-y-2">
        {data.map((item) => {
          const widthPct = max > 0 ? Math.min(100, (item.count / max) * 100) : 0;
          return (
            <li
              key={item.holder}
              className="grid grid-cols-[auto_1fr_auto_auto] items-center gap-2 py-1.5 border-b border-border/30 last:border-b-0"
            >
              <Avatar name={item.holder} />
              <span className="text-sm truncate">{item.holder}</span>
              <div className="w-12 h-[1.5px] bg-muted/40 rounded-full overflow-hidden">
                <div
                  data-testid="holder-mini-bar-fill"
                  className="h-full bg-primary/40"
                  style={{ width: `${widthPct}%` }}
                />
              </div>
              <span className="text-xs tabular-nums bg-muted text-muted-foreground rounded-full px-2 py-0.5 min-w-[2rem] text-center">
                {item.count}
              </span>
            </li>
          );
        })}
      </ul>
    </section>
  );
}

function Avatar({ name }: { name: string }) {
  const ch = name.slice(0, 1);
  return (
    <span className="size-5 rounded-full bg-muted flex items-center justify-center text-[10px] text-muted-foreground font-medium">
      {ch}
    </span>
  );
}
