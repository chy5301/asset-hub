import { Link, Outlet, useMatchRoute } from "@tanstack/react-router";
import { Toaster } from "@/components/ui/sonner";
import { ThemeToggle } from "@/components/theme/theme-toggle";
import { ErrorBoundary } from "@/components/feedback/error-boundary";

const NAV_ITEMS = [
  // 资产列表实际在 `/`（routes/index.tsx），不是 `/assets`
  { to: "/", label: "资产" },
  // `/types` 路由由 PR-3 T35 创建；PR-2 阶段尚未注册到 router 类型表，
  // 临时用 `as '/'` 类型谎言绕过 strict typing。运行时点击会 404，是 plan 已声明的预期行为，
  // PR-3 T35 落地后此 cast 即可移除。
  { to: "/types" as "/", label: "类型" },
] as const;

function NavBar() {
  const matchRoute = useMatchRoute();
  return (
    <nav
      className="border-b border-border bg-background"
      aria-label="主导航"
    >
      <div className="mx-auto flex h-10 max-w-[1400px] items-center gap-6 px-6">
        {NAV_ITEMS.map((item) => {
          const active = !!matchRoute({ to: item.to, fuzzy: true });
          return (
            <Link
              key={item.to}
              to={item.to}
              // `/` 路由要求显式传 search（TanStack Router strict typing），
              // 复用 assetsSearchSchema 默认值；`/types as '/'` cast 复用同 shape，
              // 运行时点击 404 由 PR-3 T35 路由文件落地后修复。
              search={{ sort: "asset_code", page: 1, pageSize: 50 }}
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
