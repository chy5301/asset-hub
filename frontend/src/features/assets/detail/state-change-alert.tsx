import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent,
  AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { toast } from 'sonner';
import { useChangeAssetStatusMutation } from '@/api/hooks/assets';
import { STATE_CHANGE_ACTIONS, type StateChangeKey } from './state-change-actions';
import { toFriendlyMessage } from '@/lib/error';
import type { components } from '@/api/generated/schema';

type AssetRead = components['schemas']['AssetRead'];

interface StateChangeAlertProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  asset: AssetRead;
  actionKey: StateChangeKey;
}

export function StateChangeAlert({ open, onOpenChange, asset, actionKey }: StateChangeAlertProps) {
  const action = STATE_CHANGE_ACTIONS[actionKey];
  const mutation = useChangeAssetStatusMutation(asset.id);

  async function confirm() {
    try {
      await mutation.mutateAsync(action.toStatus);
      toast.success(`${action.verb}成功`);
      onOpenChange(false);
    } catch (err) {
      toast.error(toFriendlyMessage(err));
    }
  }

  if (!action.needsConfirm) return null;

  return (
    <AlertDialog open={open} onOpenChange={onOpenChange}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>{action.confirmTitle}</AlertDialogTitle>
          <AlertDialogDescription>
            {action.confirmBody?.(asset)}
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel disabled={mutation.isPending}>取消</AlertDialogCancel>
          <AlertDialogAction
            onClick={confirm}
            disabled={mutation.isPending}
          >
            {mutation.isPending ? action.inProgressVerb : (action.confirmAction ?? '确认')}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
