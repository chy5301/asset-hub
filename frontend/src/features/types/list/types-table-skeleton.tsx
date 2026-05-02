import { Skeleton } from '@/components/ui/skeleton';

export function TypesTableSkeleton() {
  return (
    <div className="space-y-2">
      {Array.from({ length: 5 }).map((_, i) => (
        <div
          key={i}
          className="flex items-center gap-4 rounded border border-border px-4 py-3"
        >
          <Skeleton className="h-4 w-32" />
          <Skeleton className="h-4 w-16" />
          <Skeleton className="h-4 w-12" />
          <Skeleton className="ml-auto h-4 w-8" />
        </div>
      ))}
    </div>
  );
}
