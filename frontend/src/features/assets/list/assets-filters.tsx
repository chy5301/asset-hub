import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "@tanstack/react-router";
import { Archive, Moon } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { StatusFilterToggle } from "@/components/status/status-filter-toggle";
import { useAssetTypesQuery } from "@/api/hooks/types";
import {
  ASSET_STATUS_VALUES,
  type AssetsSearch,
} from "@/features/assets/list/search-schema";
import { STATUS_META } from "@/features/assets/status-labels";
import { debounce } from "@/lib/debounce";

interface AssetsFiltersProps {
  search: AssetsSearch;
}

const ALL = "__ALL__";

export function AssetsFilters({ search }: AssetsFiltersProps) {
  const navigate = useNavigate({ from: "/" });
  const typesQuery = useAssetTypesQuery();

  const [qLocal, setQLocal] = useState(search.q ?? "");
  // 拉回外部变化（重置/浏览器后退/直接改 URL）。自身 push 后 URL 与 qLocal 已经一致，
  // setState 会被 React noop 跳过，不会丢字。
  useEffect(() => {
    setQLocal(search.q ?? "");
  }, [search.q]);

  const pushQ = useMemo(
    () =>
      debounce((value: string) => {
        navigate({
          search: (prev) => ({ ...prev, q: value || undefined, page: 1 }),
        });
      }, 300),
    [navigate],
  );

  const onQChange = (value: string) => {
    setQLocal(value);
    pushQ(value);
  };

  const onSelectChange = (key: keyof AssetsSearch) => (value: string) => {
    navigate({
      search: (prev) =>
        ({
          ...prev,
          [key]: value === ALL ? undefined : value,
          page: 1,
        } as AssetsSearch),
    });
  };

  const onHolderCommit = (value: string) => {
    navigate({
      search: (prev) => ({ ...prev, holder: value || undefined, page: 1 }),
    });
  };

  const onToggleRetired = (pressed: boolean) => {
    navigate({
      search: (prev) => ({
        ...prev,
        show_retired: pressed || undefined,
        page: 1,
      }),
    });
  };

  const onToggleDisposed = (pressed: boolean) => {
    navigate({
      search: (prev) => ({
        ...prev,
        show_disposed: pressed || undefined,
        page: 1,
      }),
    });
  };

  const onReset = () => {
    navigate({
      search: () => ({ page: 1, pageSize: search.pageSize }) as AssetsSearch,
    });
    setQLocal("");
  };

  return (
    <div className="flex flex-wrap items-center gap-3">
      <Input
        value={qLocal}
        onChange={(e) => onQChange(e.target.value)}
        placeholder="关键词（名称 / 编号 / 备注）"
        className="w-64"
        aria-label="关键词搜索"
      />

      <Select
        value={search.type ?? ALL}
        onValueChange={onSelectChange("type")}
      >
        <SelectTrigger className="w-40" aria-label="类型筛选">
          <SelectValue placeholder="类型" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value={ALL}>全部类型</SelectItem>
          {typesQuery.data?.map((t: { id: string; name: string }) => (
            <SelectItem key={t.id} value={t.id}>
              {t.name}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      <Select
        value={search.status ?? ALL}
        onValueChange={onSelectChange("status")}
      >
        <SelectTrigger className="w-32" aria-label="状态筛选">
          <SelectValue placeholder="状态" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value={ALL}>全部状态</SelectItem>
          {ASSET_STATUS_VALUES.map((s) => (
            <SelectItem key={s} value={s}>
              {STATUS_META[s].label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      <HolderInput initial={search.holder ?? ""} onCommit={onHolderCommit} />

      <StatusFilterToggle
        pressed={!!search.show_retired}
        onPressedChange={onToggleRetired}
        icon={Moon}
        label="显示退役"
        status="retired"
      />
      <StatusFilterToggle
        pressed={!!search.show_disposed}
        onPressedChange={onToggleDisposed}
        icon={Archive}
        label="显示注销"
        status="disposed"
      />

      <Button variant="outline" size="sm" onClick={onReset}>
        重置
      </Button>
    </div>
  );
}

interface HolderInputProps {
  initial: string;
  onCommit: (value: string) => void;
}

function HolderInput({ initial, onCommit }: HolderInputProps) {
  const [v, setV] = useState(initial);
  const lastCommittedRef = useRef(initial);

  // 仅当外部 prop 变化（重置、URL 直改、浏览器导航）且非自身 commit 触发时同步本地。
  useEffect(() => {
    if (initial !== lastCommittedRef.current) {
      lastCommittedRef.current = initial;
      setV(initial);
    }
  }, [initial]);

  const commit = () => {
    if (v === lastCommittedRef.current) return;
    lastCommittedRef.current = v;
    onCommit(v);
  };

  return (
    <Input
      value={v}
      onChange={(e) => setV(e.target.value)}
      onBlur={commit}
      onKeyDown={(e) => {
        if (e.key === "Enter") {
          e.currentTarget.blur();
        }
      }}
      placeholder="保管人"
      className="w-40"
      aria-label="保管人筛选"
    />
  );
}
