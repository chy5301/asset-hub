import { describe, expect, it } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { http, HttpResponse } from 'msw';
import { setupServer } from 'msw/node';
import { useUndoLastTransitionMutation } from '@/api/hooks/transitions';

// 复用全局 MSW server（setup.ts 已 listen + afterEach resetHandlers）
type MswServer = ReturnType<typeof setupServer>;
const server = (globalThis as unknown as { __mswServer: MswServer }).__mswServer;

const wrapper = ({ children }: { children: React.ReactNode }) => {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
};

describe('useUndoLastTransitionMutation', () => {
  it('POST undo + 返回被撤销的 transition', async () => {
    server.use(
      http.post('http://localhost:3000/api/assets/abc/transitions/undo', () =>
        HttpResponse.json({
          id: 't1',
          asset_id: 'abc',
          kind: 'CHECKOUT_INTERNAL',
          from_status: 'IDLE',
          to_status: 'IN_USE',
          created_at: '2026-05-01T00:00:00Z',
        }),
      ),
    );
    const { result } = renderHook(() => useUndoLastTransitionMutation('abc'), { wrapper });
    const data = await result.current.mutateAsync();
    expect(data.kind).toBe('CHECKOUT_INTERNAL');
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
  });
});
