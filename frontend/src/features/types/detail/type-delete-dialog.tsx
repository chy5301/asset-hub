import { useState } from 'react';
import { toast } from 'sonner';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { useAssetsQuery } from '@/api/hooks/assets';
import { useDeleteTypeMutation } from '@/api/hooks/types';
import { toFriendlyMessage } from '@/lib/error';
import type { components } from '@/api/generated/schema';

type TypeRead = components['schemas']['TypeRead'];

interface Props {
  type: TypeRead;
  onClose: () => void;
  onDeleted?: () => void;
}

export function TypeDeleteDialog({ type, onClose, onDeleted }: Props) {
  const [confirmInput, setConfirmInput] = useState('');

  const refQuery = useAssetsQuery({
    type: type.id,
    // page/pageSize/sort 被 toServerParams 过滤不发往后端；服务端总返完整 type 过滤列表。pageSize 取 schema-valid 默认值。
    page: 1,
    pageSize: 50,
    sort: 'asset_code',
  });
  const deleteMut = useDeleteTypeMutation();

  const refCount = refQuery.data?.length ?? 0;
  const hasRefs = refCount > 0 || refQuery.isError;
  const inputMatches = confirmInput.trim() === type.name;
  const canDelete = !hasRefs && inputMatches && !deleteMut.isPending && !refQuery.isLoading;

  async function handleDelete() {
    try {
      await deleteMut.mutateAsync(type.id);
      toast.success(`已删除类型 '${type.name}'`);
      onDeleted?.();
      onClose();
    } catch (e) {
      toast.error(toFriendlyMessage(e));
    }
  }

  return (
    <Dialog open onOpenChange={(o) => !o && onClose()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>删除类型 '{type.name}'</DialogTitle>
          <DialogDescription>
            {refQuery.isError
              ? '无法确认引用数，请关闭后重试。'
              : hasRefs
                ? `该类型仍有 ${refCount} 个资产引用，请先删除/迁移所有引用此类型的资产。`
                : `此操作不可撤销。请输入完整类型名 '${type.name}' 以确认。`}
          </DialogDescription>
        </DialogHeader>

        {!hasRefs && (
          <Input
            value={confirmInput}
            onChange={(e) => setConfirmInput(e.target.value)}
            placeholder={`请输入完整类型名 '${type.name}'`}
            autoFocus
          />
        )}

        <DialogFooter>
          <Button variant="outline" onClick={onClose}>
            取消
          </Button>
          <Button
            variant="destructive"
            disabled={!canDelete}
            onClick={handleDelete}
          >
            {deleteMut.isPending ? '删除中…' : '永久删除'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
