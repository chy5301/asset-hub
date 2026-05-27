import { Archive, HelpCircle, Moon } from "lucide-react";

import { StatusFilterToggle } from "@/components/status/status-filter-toggle";

import type { DashboardSearch } from "./search-schema";

interface DashboardHeaderProps {
  includeRetired: boolean;
  includeDisposed: boolean;
  onToggle: (next: DashboardSearch) => void;
}

/**
 * 看板顶栏: h1 + 副标 + inline pill toggle (spec §B.fd3 基线对齐).
 *
 * 形态约束: 拒绝 SaaS 模板的"右上角 standalone toggle button";
 * inline pill 形态 + dot 前缀指示 on/off + status token 弱化版 active 态.
 */
export function DashboardHeader({ includeRetired, includeDisposed, onToggle }: DashboardHeaderProps) {
  return (
    <div className="mb-8 flex items-baseline justify-between">
      <div className="flex flex-col gap-1">
        <h1 className="text-3xl font-medium tracking-tight">看板</h1>
        <p className="text-sm text-muted-foreground">实时盘点 + 闲置督促</p>
      </div>

      <div className="flex items-center gap-3">
        <StatusFilterToggle
          pressed={includeRetired}
          onPressedChange={(next) =>
            onToggle({ include_retired: next, include_disposed: includeDisposed })
          }
          icon={Moon}
          label="显示退役"
          status="retired"
        />
        <StatusFilterToggle
          pressed={includeDisposed}
          onPressedChange={(next) =>
            onToggle({ include_retired: includeRetired, include_disposed: next })
          }
          icon={Archive}
          label="显示注销"
          status="disposed"
        />
        <HelpCircle className="size-3.5 text-muted-foreground/60" aria-label="提示">
          <title>默认排除显示退役/显示注销(与列表一致)</title>
        </HelpCircle>
      </div>
    </div>
  );
}

