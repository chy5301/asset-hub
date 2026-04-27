import { useState } from "react";
import { Check, Copy } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";

interface CopyableTextProps {
  value: string;
  toastLabel: string;
}

/**
 * 标识符类长字符串的复制 UI（SN / 资产 ID / asset_code 等）。
 */
export function CopyableText({ value, toastLabel }: CopyableTextProps) {
  const [copied, setCopied] = useState(false);
  return (
    <span className="inline-flex items-center gap-2">
      <span className="font-code">{value}</span>
      <Button
        variant="ghost"
        size="icon"
        className="h-6 w-6"
        aria-label={`复制${toastLabel}`}
        onClick={async () => {
          await navigator.clipboard.writeText(value);
          setCopied(true);
          toast.success(`${toastLabel}已复制`);
          setTimeout(() => setCopied(false), 1500);
        }}
      >
        {copied ? <Check className="h-3 w-3" /> : <Copy className="h-3 w-3" />}
      </Button>
    </span>
  );
}
