import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { toast } from "sonner";
import { useDeleteAsset } from "@/api/hooks/assets";
import { toFriendlyMessage } from "@/lib/error";
import { TOAST, PENDING_TEXT } from "@/features/assets/form/form-toast";

interface DeleteAssetAlertProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  asset: { id: string; name: string; asset_code: string };
  /** 删除成功后回调，调用方决定是否 navigate */
  onDeleted?: () => void;
}

export function DeleteAssetAlert({
  open,
  onOpenChange,
  asset,
  onDeleted,
}: DeleteAssetAlertProps) {
  const mutation = useDeleteAsset();

  async function confirm() {
    try {
      await mutation.mutateAsync(asset.id);
      toast.success(TOAST.DELETE_SUCCESS);
      onOpenChange(false);
      onDeleted?.();
    } catch (err) {
      toast.error(toFriendlyMessage(err));
    }
  }

  return (
    <AlertDialog open={open} onOpenChange={onOpenChange}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>确认删除？</AlertDialogTitle>
          <AlertDialogDescription className="space-y-2">
            <span className="block">
              <strong>{asset.name}</strong> ·{" "}
              <span className="font-code">{asset.asset_code}</span> 将被永久删除，
              所有关联的派发记录、附件元数据也会清空。
            </span>
            <span className="block text-destructive font-medium">
              此操作不可撤销。
            </span>
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel disabled={mutation.isPending}>取消</AlertDialogCancel>
          <AlertDialogAction
            onClick={confirm}
            disabled={mutation.isPending}
            className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
          >
            {mutation.isPending ? PENDING_TEXT.DELETE : "确认删除"}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
