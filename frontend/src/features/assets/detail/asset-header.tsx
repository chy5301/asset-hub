import { Link } from "@tanstack/react-router";
import { Button } from "@/components/ui/button";
import { formatDateTime } from "@/lib/date";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { StatusBadge } from "@/components/status/status-badge";
import type { components } from "@/api/generated/schema";
import { CHECKOUT_VERB, RETURN_VERB } from "./checkout-actions";

type AssetRead = components["schemas"]["AssetRead"];
type CheckoutRead = components["schemas"]["CheckoutRead"];

interface AssetHeaderProps {
  asset: AssetRead;
  typeName: string | undefined;
  currentCheckout: CheckoutRead | null;
  onCheckout: () => void;
  onReturn: () => void;
}

export function AssetHeader({
  asset,
  typeName,
  currentCheckout,
  onCheckout,
  onReturn,
}: AssetHeaderProps) {
  return (
    <header className="flex items-start justify-between gap-4">
      <div className="space-y-1">
        <Link
          to="/"
          search={{ sort: "asset_code", page: 1, pageSize: 50 }}
          className="text-sm text-muted-foreground hover:text-foreground transition-colors"
        >
          ← 返回列表
        </Link>
        <h1 className="text-2xl font-semibold">{asset.name}</h1>
        <div className="flex items-center gap-3">
          <span className="text-sm text-muted-foreground">
            {typeName ?? "未知类型"}
          </span>
          <StatusBadge status={asset.status} />
        </div>
        {asset.status === "IN_USE" && currentCheckout && (
          <p className="text-sm text-muted-foreground">
            当前派发给 ·{" "}
            <span className="text-foreground">{currentCheckout.holder}</span>
            {currentCheckout.location ? <> · {currentCheckout.location}</> : null}
            {" · 自 "}
            <time className="font-code">
              {formatDateTime(currentCheckout.checked_out_at)}
            </time>
          </p>
        )}
      </div>
      <CtaButton
        status={asset.status}
        onCheckout={onCheckout}
        onReturn={onReturn}
      />
    </header>
  );
}

function CtaButton({
  status,
  onCheckout,
  onReturn,
}: {
  status: AssetRead["status"];
  onCheckout: () => void;
  onReturn: () => void;
}) {
  if (status === "IDLE") {
    return <Button onClick={onCheckout}>{CHECKOUT_VERB}</Button>;
  }
  if (status === "IN_USE") {
    return <Button onClick={onReturn}>{RETURN_VERB}</Button>;
  }
  const reason =
    status === "MAINTENANCE"
      ? "维护中的资产不可派发"
      : "已退役的资产不可派发";
  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          {/* 禁用按钮不触发原生事件，需用 span 包裹才能显示 tooltip */}
          <span tabIndex={0}>
            <Button disabled>{CHECKOUT_VERB}</Button>
          </span>
        </TooltipTrigger>
        <TooltipContent>{reason}</TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}
