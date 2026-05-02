import { describe, expect, it } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { http, HttpResponse } from 'msw';
import { setupServer } from 'msw/node';
import {
  useTypeQuery,
  useCreateTypeMutation,
  useUpdateTypeMutation,
  useDeleteTypeMutation,
} from '@/api/hooks/types';

// 复用全局 MSW server（setup.ts 已 listen + afterEach resetHandlers）
type MswServer = ReturnType<typeof setupServer>;
const server = (globalThis as unknown as { __mswServer: MswServer }).__mswServer;

const wrapper = ({ children }: { children: React.ReactNode }) => {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
};

describe('use-types-mutations', () => {
  it('useTypeQuery 拉单个 type', async () => {
    server.use(
      http.get('http://localhost:3000/api/types/abc', () =>
        HttpResponse.json({
          id: 'abc',
          name: 'NB',
          code_prefix: 'NB',
          description: null,
          custom_fields: [],
          created_at: '2026-05-01T00:00:00Z',
          updated_at: '2026-05-01T00:00:00Z',
        }),
      ),
    );
    const { result } = renderHook(() => useTypeQuery('abc'), { wrapper });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.name).toBe('NB');
  });

  it('useCreateTypeMutation POST + 成功 invalidate', async () => {
    server.use(
      http.post('http://localhost:3000/api/types', () =>
        HttpResponse.json(
          {
            id: 'new',
            name: 'X',
            code_prefix: 'XX',
            description: null,
            custom_fields: [],
            created_at: '2026-05-01T00:00:00Z',
            updated_at: '2026-05-01T00:00:00Z',
          },
          { status: 201 },
        ),
      ),
    );
    const { result } = renderHook(() => useCreateTypeMutation(), { wrapper });
    await result.current.mutateAsync({
      name: 'X',
      code_prefix: 'XX',
      custom_fields: [],
    });
    // mutateAsync 解决后等待 React Query 状态更新
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
  });

  it('useUpdateTypeMutation PATCH', async () => {
    server.use(
      http.patch('http://localhost:3000/api/types/abc', () =>
        HttpResponse.json({
          id: 'abc',
          name: 'New',
          code_prefix: 'NB',
          description: null,
          custom_fields: [],
          created_at: '2026-05-01T00:00:00Z',
          updated_at: '2026-05-01T00:00:00Z',
        }),
      ),
    );
    const { result } = renderHook(() => useUpdateTypeMutation(), { wrapper });
    const data = await result.current.mutateAsync({
      id: 'abc',
      body: { name: 'New' },
    });
    expect(data.name).toBe('New');
  });

  it('useDeleteTypeMutation DELETE', async () => {
    server.use(
      http.delete('http://localhost:3000/api/types/abc', () => HttpResponse.text(null, { status: 204 })),
    );
    const { result } = renderHook(() => useDeleteTypeMutation(), { wrapper });
    await result.current.mutateAsync('abc');
    // mutateAsync 解决后等待 React Query 状态更新
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
  });
});
