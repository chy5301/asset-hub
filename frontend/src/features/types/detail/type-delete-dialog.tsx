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

  // ref_count 通过资产列表查询计算；GET /api/assets 返回 AssetRead[] flat array，
  // 取 data.length（不是 data.total），与 RefCountCell 同源教训保持一致。
  const refQuery = useAssetsQuery({
    type: type.id,
    page: 1,
    pageSize: 1,
    sort: 'asset_code',
  });
  const deleteMut = useDeleteTypeMutation();

  const refCount = refQuery.data?.length ?? 0;
  const hasRefs = refCount > 0;
  const inputMatches = confirmInput.trim() === type.name;
  const canDelete = !hasRefs && inputMatches && !deleteMut.isPending;

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
            {hasRefs
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
