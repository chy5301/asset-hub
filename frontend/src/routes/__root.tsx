import { createRootRoute } from "@tanstack/react-router";
import { TanStackRouterDevtools } from "@tanstack/react-router-devtools";
import { ReactQueryDevtools } from "@tanstack/react-query-devtools";
import { AppLayout } from "@/components/layout/app-layout";

function RootWithDevtools() {
  return (
    <>
      <AppLayout />
      {import.meta.env.DEV && (
        <>
          <TanStackRouterDevtools />
          <ReactQueryDevtools initialIsOpen={false} />
        </>
      )}
    </>
  );
}

export const Route = createRootRoute({
  component: RootWithDevtools,
});
