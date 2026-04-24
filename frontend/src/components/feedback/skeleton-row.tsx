import { Skeleton } from "@/components/ui/skeleton";

interface SkeletonRowProps {
  columns?: number;
  rows?: number;
}

export function SkeletonRow({ columns = 8, rows = 10 }: SkeletonRowProps) {
  return (
    <>
      {Array.from({ length: rows }).map((_, rIdx) => (
        <tr key={rIdx} className="border-b border-border">
          {Array.from({ length: columns }).map((_, cIdx) => (
            <td key={cIdx} className="px-3 py-2.5">
              <Skeleton className="h-4 w-full max-w-[120px]" />
            </td>
          ))}
        </tr>
      ))}
    </>
  );
}
