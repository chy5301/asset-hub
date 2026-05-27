import type { ReactNode } from "react";

interface DetailPageShellProps {
  /** 返回链接 slot（页面提供 typed <Link>，沿用 NotFoundPanel 的 backLink slot 模式）。 */
  backLink: ReactNode;
  /** 主标题文本（置于 h1.text-2xl，详情档 type scale）。 */
  title: ReactNode;
  /** 标题旁配饰（如逾期角标），可选。 */
  titleAccessory?: ReactNode;
  /** 标题下方元信息行，可选。 */
  meta?: ReactNode;
  /** 右侧操作区，可选。 */
  actions?: ReactNode;
  children: ReactNode;
}

/** 资产 / 类型详情页共享骨架：居中 960 窄栏 + 返回 + 标题/meta/actions + 正文。 */
export function DetailPageShell({
  backLink,
  title,
  titleAccessory,
  meta,
  actions,
  children,
}: DetailPageShellProps) {
  return (
    <main className="mx-auto max-w-[960px] space-y-10 px-4 py-8">
      <header className="flex items-start justify-between gap-4">
        <div className="space-y-1">
          {backLink}
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-semibold">{title}</h1>
            {titleAccessory}
          </div>
          {meta}
        </div>
        {actions}
      </header>
      {children}
    </main>
  );
}
