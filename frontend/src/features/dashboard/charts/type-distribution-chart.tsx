/**
 * 类型分布 donut.
 *
 * Recharts PieChart:
 * - innerRadius 62% + 2deg paddingAngle (spec §B.fd5)
 * - 中心大字总数 (破纯空 donut)
 * - 6 槽 chart token 哈希派色稳定 (chart-token.ts)
 * - inline ul + 圆点 legend (Pie 不挂 Recharts Legend, 简洁)
 *
 * 空态: Task 14 EmptyCard 替换前的 inline placeholder, 文案 "尚未定义任何类型" 保留.
 * 注: isAnimationActive={false} 在 jsdom 下避免动画状态干扰断言, 真实浏览器仍渲染最终态.
 */
import { Cell, Pie, PieChart, ResponsiveContainer } from "recharts";

import type { TypeDistributionItem } from "@/features/assets/types";

import { TypeEmpty } from "../empty-states/type-empty";

import { typeIdToChartTokenVar } from "./chart-token";

interface Props {
  data: TypeDistributionItem[];
}

export function TypeDistributionChart({ data }: Props) {
  if (data.length === 0) return <TypeEmpty />;

  const total = data.reduce((sum, item) => sum + item.count, 0);

  return (
    <section className="rounded-lg border bg-card p-6 flex flex-col">
      <h2 className="text-base font-medium mb-4">类型分布</h2>
      <div className="flex items-center gap-6 flex-1">
        <div className="relative size-32 shrink-0">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={data}
                dataKey="count"
                nameKey="type_name"
                innerRadius="62%"
                outerRadius="100%"
                paddingAngle={2}
                stroke="none"
                isAnimationActive={false}
              >
                {data.map((d) => (
                  <Cell key={d.type_id} fill={typeIdToChartTokenVar(d.type_id)} />
                ))}
              </Pie>
            </PieChart>
          </ResponsiveContainer>
          <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
            <span className="text-2xl font-medium tabular-nums">{total}</span>
            <span className="text-[10px] text-muted-foreground">件</span>
          </div>
        </div>
        <ul className="flex-1 space-y-1.5 text-xs">
          {data.map((item) => (
            <li key={item.type_id} className="flex items-center gap-2">
              <span
                className="size-2 rounded-sm"
                style={{ background: typeIdToChartTokenVar(item.type_id) }}
              />
              <span className="flex-1 truncate">{item.type_name}</span>
              <span className="tabular-nums text-muted-foreground">{item.count}</span>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}
