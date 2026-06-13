import { useState } from "react";
import { Undo2 } from "lucide-react";
import { toast } from "sonner";

import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";
import { useUndoLastTransitionMutation } from "@/api/hooks/transitions";
import { toFriendlyMessage } from "@/lib/error";

export function UndoLastTransitionAlert({ assetId }: { assetId: string }) {
  const [open, setOpen] = useState(false);
  const mutation = useUndoLastTransitionMutation(assetId);

  async function confirm() {
    try {
      await mutation.mutateAsync();
      toast.success("已撤销上一次流转");
      setOpen(false);
    } catch (err) {
      toast.error(toFriendlyMessage(err));
    }
  }

  return (
    <AlertDialog open={open} onOpenChange={setOpen}>
      <AlertDialogTrigger asChild>
        <Button variant="outline" size="sm" className="gap-1.5">
          <Undo2 className="size-3.5" aria-hidden />
          撤销上一次
        </Button>
      </AlertDialogTrigger>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>撤销上一次流转？</AlertDialogTitle>
          <AlertDialogDescription className="space-y-2">
            <span className="block">
              将<strong>物理删除</strong>最近一条流转记录，并把资产状态/保管人/位置回退到该记录发生前。
            </span>
            <span className="block text-destructive font-medium">
              此操作不可恢复（无法 redo）。
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
            {mutation.isPending ? "撤销中…" : "确认撤销"}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
