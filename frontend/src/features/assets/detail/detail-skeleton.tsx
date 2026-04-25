// frontend/src/features/assets/detail/detail-skeleton.tsx
import { Skeleton } from "@/components/ui/skeleton";

/**
 * 详情页三态壳的 loading 骨架。
 * 不复用 M2c-1 的 SkeletonRow——那是表格行用的。
 * 模拟详情页的单列结构：Header + 通用字段行 + 附件宫格 + Timeline。
 */
export function DetailSkeleton() {
  return (
    <div className="mx-auto max-w-[960px] space-y-10 px-4 py-8">
      {/* Header */}
      <div className="space-y-2">
        <Skeleton className="h-4 w-24" />
        <Skeleton className="h-7 w-64" />
        <Skeleton className="h-4 w-48" />
      </div>

      {/* 通用字段 8 行 */}
      <div className="space-y-3">
        <Skeleton className="h-6 w-24" />
        {Array.from({ length: 8 }).map((_, i) => (
          <div key={i} className="flex gap-4">
            <Skeleton className="h-4 w-24" />
            <Skeleton className="h-4 w-48" />
          </div>
        ))}
      </div>

      {/* 附件宫格 */}
      <div className="space-y-3">
        <Skeleton className="h-6 w-24" />
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="aspect-square w-full rounded-md" />
          ))}
        </div>
      </div>

      {/* Timeline */}
      <div className="space-y-3">
        <Skeleton className="h-6 w-24" />
        {Array.from({ length: 3 }).map((_, i) => (
          <div key={i} className="flex gap-4">
            <Skeleton className="h-3 w-3 rounded-full" />
            <div className="flex-1 space-y-2">
              <Skeleton className="h-4 w-40" />
              <Skeleton className="h-3 w-64" />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
