import { Link, useNavigate } from "@tanstack/react-router";
import { Clock, MoreHorizontal } from "lucide-react";
import { useState } from "react";

import { useTransitionsQuery } from "@/api/hooks/transitions";
import type { AssetRead, TransitionKind } from "@/features/assets/types";
import { StatusBadge } from "@/components/status/status-badge";
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
import { calcOverdue } from "@/lib/overdue";
import { cn } from "@/lib/utils";

import { MENU_ACTIONS, PRIMARY_ACTIONS } from "./available-transitions";
import { CheckoutDialog } from "./checkout-dialog";
import { DisposeAlertDialog } from "./dispose-alert-dialog";
import { RelocateDialog } from "./relocate-dialog";
import { RetireAlertDialog } from "./retire-alert-dialog";
import { ReturnDialog } from "./return-dialog";
import { SimpleTransitionDialog } from "./simple-transition-dialog";
import { TransferHolderDialog } from "./transfer-holder-dialog";

interface AssetHeaderProps {
  asset: AssetRead;
  onDelete: () => void;
}

function useOverdueForOpenCheckout(
  assetId: string,
  assetStatus: AssetRead["status"],
) {
  const { data: transitions } = useTransitionsQuery(assetId);
  if (!transitions) return null;
  const closedIds = new Set(
    transitions
      .filter((t) => t.kind === "RETURN" && t.closes_transition_id)
      .map((t) => t.closes_transition_id as string),
  );
  const open = transitions.find(
    (t) =>
      (t.kind === "CHECKOUT_INTERNAL" || t.kind === "CHECKOUT_EXTERNAL") &&
      !closedIds.has(t.id),
  );
  if (!open) return null;
  return calcOverdue(open.due_at, assetStatus);
}

export function AssetHeader({ asset, onDelete }: AssetHeaderProps) {
  const overdue = useOverdueForOpenCheckout(asset.id, asset.status);
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
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-semibold">{asset.name}</h1>
          {overdue && overdue.status !== "pending" && (
            <span
              className={cn(
                "inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium",
                overdue.status === "due-soon" && "bg-warning/15 text-warning-fg",
                overdue.status === "overdue" && "bg-destructive/15 text-destructive",
              )}
            >
              <Clock className="size-3" aria-hidden />
              {overdue.status === "due-soon"
                ? `还有 ${overdue.days} 天到期`
                : `逾期 ${overdue.days} 天`}
            </span>
          )}
        </div>
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
        {asset.holder && (
          <p className="text-sm text-muted-foreground">
            当前保管人 ·{" "}
            <span className="text-foreground">{asset.holder}</span>
            {asset.location ? <> · {asset.location}</> : null}
          </p>
        )}
      </div>
      <ActionArea asset={asset} onDelete={onDelete} />
    </header>
  );
}

function ActionArea({
  asset,
  onDelete,
}: {
  asset: AssetRead;
  onDelete: () => void;
}) {
  const navigate = useNavigate();
  const status = asset.status;
  const primaries = PRIMARY_ACTIONS[status];
  const menuItems = MENU_ACTIONS[status];
  const [openDialog, setOpenDialog] = useState<TransitionKind | null>(null);

  const isReadonly = status === "DISPOSED";
  const closeDialog = (open: boolean) => !open && setOpenDialog(null);

  return (
    <div className="flex items-center gap-2">
      {primaries.map((p) => (
        <Button key={p.kind} onClick={() => setOpenDialog(p.kind)}>
          {p.label}
        </Button>
      ))}

      {/* 编辑非 transition，outline 视觉分层；DISPOSED 全只读时隐藏 */}
      {!isReadonly && (
        <Button
          variant="outline"
          onClick={() =>
            navigate({ to: "/assets/$id/edit", params: { id: asset.id } })
          }
        >
          编辑
        </Button>
      )}

      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="ghost" size="icon" aria-label="更多操作">
            <MoreHorizontal className="h-4 w-4" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end">
          {menuItems.map((action) => (
            <DropdownMenuItem
              key={action.kind}
              onSelect={() => setOpenDialog(action.kind)}
            >
              {action.label}…
            </DropdownMenuItem>
          ))}

          {menuItems.length > 0 && <DropdownMenuSeparator />}

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

      {/* dialog 条件渲染：未打开则不实例化，避免每次详情页 render 都跑 9× useForm + useMutation */}
      {(openDialog === "CHECKOUT_INTERNAL" || openDialog === "CHECKOUT_EXTERNAL") && (
        <CheckoutDialog open onOpenChange={closeDialog} assetId={asset.id} kind={openDialog} />
      )}
      {openDialog === "RETURN" && (
        <ReturnDialog open onOpenChange={closeDialog} assetId={asset.id} />
      )}
      {(openDialog === "SEND_TO_MAINTENANCE" ||
        openDialog === "RECOVER_FROM_MAINTENANCE" ||
        openDialog === "REINSTATE") && (
        <SimpleTransitionDialog open onOpenChange={closeDialog} assetId={asset.id} kind={openDialog} />
      )}
      {openDialog === "RETIRE" && (
        <RetireAlertDialog open onOpenChange={closeDialog} assetId={asset.id} assetName={asset.name} />
      )}
      {openDialog === "DISPOSE" && (
        <DisposeAlertDialog open onOpenChange={closeDialog} assetId={asset.id} assetName={asset.name} />
      )}
      {openDialog === "RELOCATE" && (
        <RelocateDialog open onOpenChange={closeDialog} assetId={asset.id} />
      )}
      {openDialog === "TRANSFER_HOLDER" && (
        <TransferHolderDialog open onOpenChange={closeDialog} assetId={asset.id} />
      )}
    </div>
  );
}
