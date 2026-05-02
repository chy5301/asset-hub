import { useState } from 'react';
import { ArrowDown, ArrowUp, ChevronDown, ChevronRight, Trash2 } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';
import type { Control, UseFormSetValue, FieldErrors } from 'react-hook-form';
import { useWatch } from 'react-hook-form';
import { FieldAttributeForm } from './field-attribute-form';
import type { CreateTypeFormValues } from '../build-type-schema';

interface Props {
  control: Control<CreateTypeFormValues>;
  setValue: UseFormSetValue<CreateTypeFormValues>;
  index: number;
  total: number;
  defaultExpanded?: boolean;
  onRemove: () => void;
  onMoveUp: () => void;
  onMoveDown: () => void;
  errors?: FieldErrors<CreateTypeFormValues>;
}

export function FieldCard({
  control,
  setValue,
  index,
  total,
  defaultExpanded = false,
  onRemove,
  onMoveUp,
  onMoveDown,
  errors,
}: Props) {
  const [expanded, setExpanded] = useState(defaultExpanded);
  const f = useWatch({ control, name: `custom_fields.${index}` });

  return (
    <Collapsible open={expanded} onOpenChange={setExpanded} asChild>
      <Card className="overflow-hidden">
        {/* 折叠态行（始终可见）*/}
        <div className="flex items-center gap-3 p-3">
          <CollapsibleTrigger asChild>
            <button
              type="button"
              className="text-muted-foreground hover:text-foreground cursor-pointer rounded focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              aria-label={expanded ? '折叠' : '展开'}
            >
              {expanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
            </button>
          </CollapsibleTrigger>
          <span className="font-mono text-sm">{f?.key || '(未命名字段)'}</span>
          <Badge variant="outline" className="text-xs">
            {f?.type || '?'}
          </Badge>
          {f?.required && <span className="text-destructive text-sm">*</span>}
          <div className="flex-1" />
          {expanded && (
            <>
              <Button
                type="button"
                variant="ghost"
                size="icon"
                onClick={onMoveUp}
                disabled={index === 0}
                aria-label="上移"
              >
                <ArrowUp className="h-4 w-4" />
              </Button>
              <Button
                type="button"
                variant="ghost"
                size="icon"
                onClick={onMoveDown}
                disabled={index === total - 1}
                aria-label="下移"
              >
                <ArrowDown className="h-4 w-4" />
              </Button>
            </>
          )}
          <Button
            type="button"
            variant="ghost"
            size="icon"
            onClick={onRemove}
            aria-label="删除字段"
            className="text-muted-foreground hover:text-destructive"
          >
            <Trash2 className="h-4 w-4" />
          </Button>
        </div>

        {/* 展开态：Radix Collapsible 驱动的真 200ms 动画（F1 修订）*/}
        <CollapsibleContent className="data-[state=open]:animate-collapsible-down data-[state=closed]:animate-collapsible-up motion-reduce:animate-none border-t border-border overflow-hidden">
          <FieldAttributeForm
            control={control}
            setValue={setValue}
            index={index}
            errors={errors}
          />
        </CollapsibleContent>
      </Card>
    </Collapsible>
  );
}
