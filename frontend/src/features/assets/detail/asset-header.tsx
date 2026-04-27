import { Link, useNavigate } from "@tanstack/react-router";
import { MoreHorizontal } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { formatDateTime } from "@/lib/date";
import { StatusBadge } from "@/components/status/status-badge";
import type { components } from "@/api/generated/schema";
import { CHECKOUT_VERB, RETURN_VERB } from "./checkout-actions";
import {
  STATE_CHANGE_ACTIONS,
  availableStateChanges,
  type StateChangeKey,
} from "./state-change-actions";

type AssetRead = components["schemas"]["AssetRead"];
type CheckoutRead = components["schemas"]["CheckoutRead"];

interface AssetHeaderProps {
  asset: AssetRead;
  currentCheckout: CheckoutRead | null;
  onCheckout: () => void;
  onReturn: () => void;
  onChangeStatus: (key: StateChangeKey) => void;
  onDelete: () => void;
}

export function AssetHeader({
  asset,
  currentCheckout,
  onCheckout,
  onReturn,
  onChangeStatus,
  onDelete,
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
          <span className="font-code text-sm text-muted-foreground">
            {asset.asset_code}
          </span>
          <span className="text-sm text-muted-foreground">·</span>
          <span className="text-sm text-muted-foreground">
            {asset.type_name ?? "未知类型"}
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
      <ActionArea
        asset={asset}
        onCheckout={onCheckout}
        onReturn={onReturn}
        onChangeStatus={onChangeStatus}
        onDelete={onDelete}
      />
    </header>
  );
}

function ActionArea({
  asset,
  onCheckout,
  onReturn,
  onChangeStatus,
  onDelete,
}: {
  asset: AssetRead;
  onCheckout: () => void;
  onReturn: () => void;
  onChangeStatus: (key: StateChangeKey) => void;
  onDelete: () => void;
}) {
  const status = asset.status;
  const stateChanges = availableStateChanges(status);
  const navigate = useNavigate();

  return (
    <div className="flex items-center gap-2">
      {/* 主按钮：按状态决定 */}
      {status === "IDLE" && (
        <Button onClick={onCheckout}>{CHECKOUT_VERB}</Button>
      )}
      {status === "IN_USE" && (
        <Button onClick={onReturn}>{RETURN_VERB}</Button>
      )}
      {status === "MAINTENANCE" && (
        <Button
          onClick={() => onChangeStatus("return_from_maintenance")}
          className="bg-emerald-600 hover:bg-emerald-700"
        >
          {STATE_CHANGE_ACTIONS.return_from_maintenance.verb}
        </Button>
      )}
      {status === "RETIRED" && (
        <Button
          onClick={() => onChangeStatus("reactivate")}
          variant="outline"
        >
          {STATE_CHANGE_ACTIONS.reactivate.verb}
        </Button>
      )}

      {/* 次按钮：仅 IDLE 显示「送修」 */}
      {status === "IDLE" && (
        <Button
          variant="outline"
          onClick={() => onChangeStatus("send_to_maintenance")}
        >
          {STATE_CHANGE_ACTIONS.send_to_maintenance.verb}
        </Button>
      )}

      {/* ⋯ 菜单 */}
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="ghost" size="icon" aria-label="更多操作">
            <MoreHorizontal className="h-4 w-4" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end">
          <DropdownMenuItem
            onSelect={() =>
              navigate({ to: "/assets/$id/edit", params: { id: asset.id } })
            }
          >
            编辑
          </DropdownMenuItem>

          {/* 需确认的状态切换项（IDLE/MAINTENANCE 状态下的「退役」；reactivate 已在主按钮位置） */}
          {stateChanges
            .filter(
              (k) =>
                STATE_CHANGE_ACTIONS[k].needsConfirm && k !== "reactivate",
            )
            .map((key) => (
              <DropdownMenuItem
                key={key}
                onSelect={() => onChangeStatus(key)}
              >
                {STATE_CHANGE_ACTIONS[key].verb}…
              </DropdownMenuItem>
            ))}

          <DropdownMenuSeparator />

          {status === "IN_USE" ? (
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <span tabIndex={0}>
                    <DropdownMenuItem disabled className="text-destructive">
                      删除
                    </DropdownMenuItem>
                  </span>
                </TooltipTrigger>
                <TooltipContent>需先归还</TooltipContent>
              </Tooltip>
            </TooltipProvider>
          ) : (
            <DropdownMenuItem
              onSelect={onDelete}
              className="text-destructive focus:text-destructive"
            >
              删除…
            </DropdownMenuItem>
          )}
        </DropdownMenuContent>
      </DropdownMenu>
    </div>
  );
}
