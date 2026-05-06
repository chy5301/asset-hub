/**
 * 闲置时长 Top 10 横向条形图.
 *
 * Recharts vertical BarChart:
 * - idle_days > 90: var(--destructive) 红 (强警示)
 * - idle_days ≤ 90: var(--chart-1) 蓝 dominant
 *
 * 注: plan 草稿假设 var(--checkout-internal) token, 但 M3a 未落, 改 var(--chart-1) 等价蓝.
 * 空态用 inline placeholder div, Task 14 替换为 EmptyCard 组件 (文案保留).
 */
import { Clock } from "lucide-react";
import { Bar, BarChart, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import type { IdleTopItem } from "@/features/assets/types";

import { IdleEmpty } from "../empty-states/idle-empty";

const IDLE_THRESHOLD_DAYS = 90;
const ANIMATION_MS = 480;

interface Props {
  data: IdleTopItem[];
}

export function IdleTopBarChart({ data }: Props) {
  if (data.length === 0) return <IdleEmpty />;

  return (
    <section className="rounded-lg border bg-card p-6 flex flex-col">
      <header className="mb-4 flex items-baseline justify-between">
        <h2 className="text-base font-medium">闲置时长 Top 10</h2>
        <span className="text-xs text-muted-foreground">超 90 天可考虑退役 / 重派发</span>
      </header>
      <div className="flex-1 min-h-0">
        <ResponsiveContainer width="100%" height={400}>
          <BarChart
            data={data}
            layout="vertical"
            margin={{ top: 8, right: 60, bottom: 8, left: 8 }}
          >
            <XAxis
              type="number"
              tickLine={false}
              axisLine={false}
              tick={{ fill: "var(--muted-foreground)", fontSize: 11 }}
              tickFormatter={(v: number) => `${v}d`}
            />
            <YAxis
              type="category"
              dataKey="asset_code"
              tickLine={false}
              axisLine={false}
              tick={{ fill: "var(--foreground)", fontSize: 11 }}
              width={90}
            />
            <Tooltip cursor={{ fill: "var(--muted)", opacity: 0.4 }} content={<IdleTooltip />} />
            <Bar
              dataKey="idle_days"
              radius={[0, 4, 4, 0]}
              animationDuration={ANIMATION_MS}
              animationEasing="ease-out"
              isAnimationActive
            >
              {data.map((item) => (
                <Cell
                  key={item.asset_id}
                  fill={
                    item.idle_days > IDLE_THRESHOLD_DAYS
                      ? "var(--destructive)"
                      : "var(--chart-1)"
                  }
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </section>
  );
}

interface IdleTooltipProps {
  active?: boolean;
  payload?: Array<{ payload: IdleTopItem }>;
}

function IdleTooltip({ active, payload }: IdleTooltipProps) {
  if (!active || !payload?.length) return null;
  const item = payload[0].payload;
  const overdue = item.idle_days > IDLE_THRESHOLD_DAYS;
  return (
    <div className="rounded-md border bg-popover px-3 py-2 shadow-md text-xs space-y-1">
      <div className="font-medium">{item.asset_code}</div>
      <div className="text-muted-foreground">{item.type_name}</div>
      {item.current_location && (
        <div className="text-muted-foreground">📍 {item.current_location}</div>
      )}
      <div
        className={
          overdue
            ? "text-destructive font-medium flex items-center gap-1"
            : "tabular-nums"
        }
      >
        {overdue && <Clock className="size-3" />}
        {item.idle_days} 天闲置
      </div>
    </div>
  );
}
