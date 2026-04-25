import { QueryClient } from "@tanstack/react-query";
import { isHttpError } from "@/lib/error";

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      refetchOnWindowFocus: false,
      retry: (failCount, err) => {
        if (isHttpError(err) && err.status >= 400 && err.status < 500)
          return false;
        return failCount < 2;
      },
    },
    // mutations 默认不 toast，由各 mutation 自行决定（Dialog 走 inline banner，
    // 列表 CRUD 走 toast.error）。这样 Dialog mutation 不需要再"opt out"。
  },
});
