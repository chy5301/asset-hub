import { QueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { isHttpError, toFriendlyMessage } from "@/lib/error";

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
    mutations: {
      onError: (err) => toast.error(toFriendlyMessage(err)),
    },
  },
});
