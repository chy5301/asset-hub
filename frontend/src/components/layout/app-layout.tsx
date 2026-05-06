import { Link, Outlet, useMatchRoute } from "@tanstack/react-router";
import { Toaster } from "@/components/ui/sonner";
import { ThemeToggle } from "@/components/theme/theme-toggle";
import { ErrorBoundary } from "@/components/feedback/error-boundary";
import { ASSETS_DEFAULT_SEARCH } from "@/features/assets/list/search-schema";

// §P 修订：PR-3 注册 /types 后，原 fuzzy match `to: '/'` 会让 /types 也激活"资产"
// （/ 是所有路径的前缀）。改为 fuzzy: false 对根路径做精确匹配，隔离两个分支的 active 检测。
const NAV_ITEMS = [
  // 资产列表实际在 `/`（routes/index.tsx）；fuzzy: false 防止 /types 误触发
  { to: "/" as const, label: "资产", fuzzy: false },
  // /types 注册于 PR-3 T35；fuzzy: true 让 /types/new、/types/$id 也高亮"类型"
  { to: "/types" as const, label: "类型", fuzzy: true },
  // /dashboard 注册于 PR-2 T16；fuzzy: false 无子路由
  { to: "/dashboard" as const, label: "看板", fuzzy: false },
] satisfies { to: "/" | "/types" | "/dashboard"; label: string; fuzzy: boolean }[];

function NavBar() {
  const matchRoute = useMatchRoute();
  return (
    <nav
      className="border-b border-border bg-background"
      aria-label="主导航"
    >
      <div className="mx-auto flex h-10 max-w-[1400px] items-center gap-6 px-6">
        {NAV_ITEMS.map((item) => {
          const active = !!matchRoute({ to: item.to, fuzzy: item.fuzzy });
          return (
            <Link
              key={item.to}
              to={item.to}
              // `/` 路由要求显式传 search（TanStack Router strict typing），复用 assetsSearchSchema 默认值
              {...(item.to === "/" ? { search: ASSETS_DEFAULT_SEARCH } : {})}
              className={
                active
                  ? "text-sm font-medium text-primary border-b-2 border-primary -mb-px py-2 transition-colors"
                  : "text-sm text-muted-foreground hover:text-foreground py-2 transition-colors"
              }
            >
              {item.label}
            </Link>
          );
        })}
      </div>
    </nav>
  );
}

export function AppLayout() {
  return (
    <div className="min-h-screen bg-background text-foreground">
      <header className="border-b border-border">
        <div className="mx-auto flex h-14 max-w-[1400px] items-center justify-between px-6">
          <span className="text-sm font-medium tracking-tight text-foreground">
            小组资产管理工具
          </span>
          <ThemeToggle />
        </div>
      </header>
      <NavBar />
      <main className="mx-auto max-w-[1400px] px-6 py-6">
        <ErrorBoundary>
          <Outlet />
        </ErrorBoundary>
      </main>
      <Toaster position="top-right" richColors />
    </div>
  );
}
