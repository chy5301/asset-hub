import { Link, useNavigate } from "@tanstack/react-router";
import { MoreHorizontal } from "lucide-react";
import { useState } from "react";

import type { components } from "@/api/generated/schema";
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

import {
  MENU_ACTIONS,
  PRIMARY_ACTION,
  type MenuAction,
} from "./available-transitions";
import { CheckoutDialog } from "./checkout-dialog";
import { DisposeAlertDialog } from "./dispose-alert-dialog";
import { RelocateDialog } from "./relocate-dialog";
import { RetireAlertDialog } from "./retire-alert-dialog";
import { ReturnDialog } from "./return-dialog";
import { SimpleTransitionDialog } from "./simple-transition-dialog";
import { TransferHolderDialog } from "./transfer-holder-dialog";

type AssetRead = components["schemas"]["AssetRead"];

interface AssetHeaderProps {
  asset: AssetRead;
  onDelete: () => void;
}

export function AssetHeader({ asset, onDelete }: AssetHeaderProps) {
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

type DialogKind =
  | "checkout"
  | "return"
  | "send_to_maintenance"
  | "recover_from_maintenance"
  | "reinstate"
  | "retire"
  | "dispose"
  | "relocate"
  | "transfer_holder";

function ActionArea({
  asset,
  onDelete,
}: {
  asset: AssetRead;
  onDelete: () => void;
}) {
  const navigate = useNavigate();
  const status = asset.status;
  const primary = PRIMARY_ACTION[status];
  const menuItems = MENU_ACTIONS[status];
  const [openDialog, setOpenDialog] = useState<DialogKind | null>(null);

  // DISPOSED 全只读：隐藏主按钮、菜单项里仅显示编辑（且也隐藏）+ 删除
  const isReadonly = status === "DISPOSED";

  function openMenuAction(action: MenuAction) {
    switch (action.kind) {
      case "SEND_TO_MAINTENANCE":
        return setOpenDialog("send_to_maintenance");
      case "RETIRE":
        return setOpenDialog("retire");
      case "DISPOSE":
        return setOpenDialog("dispose");
      case "RELOCATE":
        return setOpenDialog("relocate");
      case "TRANSFER_HOLDER":
        return setOpenDialog("transfer_holder");
    }
  }

  function renderPrimaryButton() {
    if (!primary) return null;
    if (primary.kind === "DISPATCH_GROUP") {
      return <Button onClick={() => setOpenDialog("checkout")}>{primary.label}</Button>;
    }
    if (primary.kind === "RETURN") {
      return <Button onClick={() => setOpenDialog("return")}>{primary.label}</Button>;
    }
    if (primary.kind === "RECOVER_FROM_MAINTENANCE") {
      return (
        <Button
          onClick={() => setOpenDialog("recover_from_maintenance")}
          className="bg-emerald-600 hover:bg-emerald-700"
        >
          {primary.label}
        </Button>
      );
    }
    if (primary.kind === "REINSTATE") {
      return (
        <Button onClick={() => setOpenDialog("reinstate")} variant="outline">
          {primary.label}
        </Button>
      );
    }
    return null;
  }

  return (
    <div className="flex items-center gap-2">
      {renderPrimaryButton()}

      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="ghost" size="icon" aria-label="更多操作">
            <MoreHorizontal className="h-4 w-4" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end">
          {!isReadonly && (
            <DropdownMenuItem
              onSelect={() =>
                navigate({ to: "/assets/$id/edit", params: { id: asset.id } })
              }
            >
              编辑
            </DropdownMenuItem>
          )}

          {menuItems.map((action) => (
            <DropdownMenuItem
              key={action.kind}
              onSelect={() => openMenuAction(action)}
            >
              {action.label}…
            </DropdownMenuItem>
          ))}

          {(menuItems.length > 0 || !isReadonly) && <DropdownMenuSeparator />}

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

      {/* Dialogs（受控 props 风格） */}
      <CheckoutDialog
        open={openDialog === "checkout"}
        onOpenChange={(o) => !o && setOpenDialog(null)}
        assetId={asset.id}
      />
      <ReturnDialog
        open={openDialog === "return"}
        onOpenChange={(o) => !o && setOpenDialog(null)}
        assetId={asset.id}
      />
      <SimpleTransitionDialog
        open={openDialog === "send_to_maintenance"}
        onOpenChange={(o) => !o && setOpenDialog(null)}
        assetId={asset.id}
        kind="SEND_TO_MAINTENANCE"
      />
      <SimpleTransitionDialog
        open={openDialog === "recover_from_maintenance"}
        onOpenChange={(o) => !o && setOpenDialog(null)}
        assetId={asset.id}
        kind="RECOVER_FROM_MAINTENANCE"
      />
      <SimpleTransitionDialog
        open={openDialog === "reinstate"}
        onOpenChange={(o) => !o && setOpenDialog(null)}
        assetId={asset.id}
        kind="REINSTATE"
      />
      <RetireAlertDialog
        open={openDialog === "retire"}
        onOpenChange={(o) => !o && setOpenDialog(null)}
        assetId={asset.id}
        assetName={asset.name}
      />
      <DisposeAlertDialog
        open={openDialog === "dispose"}
        onOpenChange={(o) => !o && setOpenDialog(null)}
        assetId={asset.id}
        assetName={asset.name}
      />
      <RelocateDialog
        open={openDialog === "relocate"}
        onOpenChange={(o) => !o && setOpenDialog(null)}
        assetId={asset.id}
      />
      <TransferHolderDialog
        open={openDialog === "transfer_holder"}
        onOpenChange={(o) => !o && setOpenDialog(null)}
        assetId={asset.id}
      />
    </div>
  );
}
