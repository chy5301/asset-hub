import { useState } from 'react';
import { type Control } from 'react-hook-form';
import { Check, ChevronsUpDown, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import { Command, CommandEmpty, CommandGroup, CommandInput, CommandItem } from '@/components/ui/command';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { FormField, FormItem, FormLabel, FormControl, FormDescription, FormMessage } from '@/components/ui/form';
import { Label } from '@/components/ui/label';
import { cn } from '@/lib/utils';
import type { FieldDef } from '../types';

const CHECKBOX_THRESHOLD = 4;

export function MultiEnumField({ def, control }: { def: FieldDef; control: Control }) {
  const options = def.options ?? [];
  const useCheckboxes = def.displayAs === 'radio' || (def.displayAs !== 'select' && options.length <= CHECKBOX_THRESHOLD);

  return (
    <FormField
      control={control}
      name={def.key}
      render={({ field }) => {
        const value: string[] = field.value ?? [];
        const toggle = (opt: string) =>
          field.onChange(value.includes(opt) ? value.filter((v) => v !== opt) : [...value, opt]);

        return (
          <FormItem>
            <FormLabel>
              {def.label ?? def.key}
              {def.required && <span className="ml-1 text-destructive">*</span>}
            </FormLabel>
            <FormControl>
              {useCheckboxes ? (
                <div className="flex flex-col gap-2">
                  {options.map((opt) => (
                    <div key={opt} className="flex items-center gap-2">
                      <Checkbox
                        id={`${def.key}-${opt}`}
                        checked={value.includes(opt)}
                        onCheckedChange={() => toggle(opt)}
                      />
                      <Label htmlFor={`${def.key}-${opt}`} className="font-normal">{opt}</Label>
                    </div>
                  ))}
                </div>
              ) : (
                <ComboboxMulti options={options} value={value} onChange={field.onChange} placeholder={def.placeholder ?? '请选择'} />
              )}
            </FormControl>
            {def.help && <FormDescription>{def.help}</FormDescription>}
            <FormMessage />
          </FormItem>
        );
      }}
    />
  );
}

function ComboboxMulti({
  options, value, onChange, placeholder,
}: {
  options: string[]; value: string[]; onChange: (v: string[]) => void; placeholder: string;
}) {
  const [open, setOpen] = useState(false);
  const toggle = (opt: string) =>
    onChange(value.includes(opt) ? value.filter((v) => v !== opt) : [...value, opt]);

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button variant="outline" role="combobox" className="w-full justify-between">
          <span className="flex flex-wrap gap-1">
            {value.length === 0 ? <span className="text-muted-foreground">{placeholder}</span>
              : value.map((v) => (
                <span key={v} className="rounded-sm bg-secondary px-1.5 text-xs">
                  {v}
                  <X className="ml-1 inline h-3 w-3 cursor-pointer" onClick={(e) => { e.stopPropagation(); toggle(v); }} />
                </span>
              ))}
          </span>
          <ChevronsUpDown className="ml-2 h-4 w-4 opacity-50" />
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-[--radix-popover-trigger-width] p-0">
        <Command>
          <CommandInput placeholder="搜索…" />
          <CommandEmpty>无匹配项</CommandEmpty>
          <CommandGroup>
            {options.map((opt) => (
              <CommandItem key={opt} onSelect={() => toggle(opt)}>
                <Check className={cn('mr-2 h-4 w-4', value.includes(opt) ? 'opacity-100' : 'opacity-0')} />
                {opt}
              </CommandItem>
            ))}
          </CommandGroup>
        </Command>
      </PopoverContent>
    </Popover>
  );
}
