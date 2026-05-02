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
import { useDeleteTypeMutation, useTypeRefCount } from '@/api/hooks/types';
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

  const { count: refCount, isLoading: refLoading, isError: refError } = useTypeRefCount(type.id);
  const deleteMut = useDeleteTypeMutation();

  const hasRefs = refCount > 0 || refError;
  const inputMatches = confirmInput.trim() === type.name;
  const canDelete = !hasRefs && inputMatches && !deleteMut.isPending && !refLoading;

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
          <DialogDescription>{describeState(refError, hasRefs, refCount, type.name)}</DialogDescription>
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

function describeState(
  isError: boolean,
  hasRefs: boolean,
  refCount: number,
  typeName: string,
): string {
  if (isError) return '无法确认引用数，请关闭后重试。';
  if (hasRefs) return `该类型仍有 ${refCount} 个资产引用，请先删除/迁移所有引用此类型的资产。`;
  return `此操作不可撤销。请输入完整类型名 '${typeName}' 以确认。`;
}
