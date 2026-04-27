import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";

export type Theme = "light" | "dark" | "system";

interface ThemeCtx {
  theme: Theme;
  setTheme: (t: Theme) => void;
}

const STORAGE_KEY = "asset-hub.theme";
const Ctx = createContext<ThemeCtx | null>(null);

function applyClass(theme: Theme) {
  const dark =
    theme === "dark" ||
    (theme === "system" &&
      window.matchMedia("(prefers-color-scheme: dark)").matches);
  document.documentElement.classList.toggle("dark", dark);
}

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [theme, setThemeState] = useState<Theme>(() => {
    const stored = localStorage.getItem(STORAGE_KEY);
    return (stored === "dark" || stored === "light" || stored === "system" ? stored : "light") as Theme;
  });

  // 主题变化时同步 html.dark；system 模式下额外监听系统切换
  // 防闪烁脚本已处理首屏，这里保障 React 水合后一致
  useEffect(() => {
    applyClass(theme);
    if (theme !== "system") return;
    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    const onChange = () => applyClass("system");
    mq.addEventListener("change", onChange);
    return () => mq.removeEventListener("change", onChange);
  }, [theme]);

  const setTheme = useCallback((next: Theme) => {
    setThemeState(next);
    localStorage.setItem(STORAGE_KEY, next);
  }, []);

  const value = useMemo<ThemeCtx>(() => ({ theme, setTheme }), [theme, setTheme]);

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useTheme() {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useTheme must be used within ThemeProvider");
  return ctx;
}
