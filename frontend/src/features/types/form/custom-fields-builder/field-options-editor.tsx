import { useState, type KeyboardEvent } from 'react';
import { X } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';

interface Props {
  value: string[];
  onChange: (next: string[]) => void;
  errorPaths?: number[]; // 哪些 index 标红（来自 superRefine）
}

export function FieldOptionsEditor({ value, onChange, errorPaths = [] }: Props) {
  const [draft, setDraft] = useState('');
  const errorSet = new Set(errorPaths);

  function handleKeyDown(e: KeyboardEvent<HTMLInputElement>) {
    if (e.key === 'Enter' && draft.trim()) {
      e.preventDefault();
      onChange([...value, draft.trim()]);
      setDraft('');
    }
  }

  function removeAt(idx: number) {
    onChange(value.filter((_, i) => i !== idx));
  }

  return (
    <div className="space-y-2">
      <div className="flex flex-wrap gap-1.5">
        {value.map((opt, idx) => (
          <Badge
            key={`${opt}-${idx}`}
            variant={errorSet.has(idx) ? 'destructive' : 'secondary'}
            className="group cursor-default pr-1"
          >
            <span className="mr-1">{opt}</span>
            <button
              type="button"
              onClick={() => removeAt(idx)}
              className="opacity-0 group-hover:opacity-100 focus-visible:opacity-100 transition-opacity hover:text-destructive cursor-pointer rounded-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              aria-label={`删除选项 ${opt}`}
            >
              <X className="h-3 w-3" />
            </button>
          </Badge>
        ))}
      </div>
      <Input
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="输入选项后按 Enter"
        className="max-w-[280px]"
      />
    </div>
  );
}
