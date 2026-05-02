import { describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { setupServer } from 'msw/node';
import { http, HttpResponse } from 'msw';
import { TypeDeleteDialog } from '@/features/types/detail/type-delete-dialog';

type MswServer = ReturnType<typeof setupServer>;
const server = (globalThis as unknown as { __mswServer: MswServer }).__mswServer;

const wrapper = ({ children }: { children: React.ReactNode }) => {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
};

const T = {
  id: 'abc',
  name: '笔记本',
  code_prefix: 'NB',
  description: null,
  custom_fields: [],
  created_at: '',
  updated_at: '',
};

describe('TypeDeleteDialog', () => {
  it('ref_count > 0 → 禁用按钮 + 提示', async () => {
    server.use(
      http.get('http://localhost:3000/api/assets', () =>
        HttpResponse.json([{ id: 'a1' }, { id: 'a2' }, { id: 'a3' }]),
      ),
    );
    render(<TypeDeleteDialog type={T} onClose={() => {}} />, { wrapper });
    await waitFor(() =>
      expect(screen.getByText(/仍有 3 个资产引用/)).toBeInTheDocument(),
    );
    expect(screen.getByRole('button', { name: /永久删除/ })).toBeDisabled();
  });

  it('ref_count = 0 → 输入完整 name 后可删', async () => {
    const user = userEvent.setup();
    const onDeleted = vi.fn();
    server.use(
      http.get('http://localhost:3000/api/assets', () =>
        HttpResponse.json([]),
      ),
      http.delete('http://localhost:3000/api/types/abc', () =>
        HttpResponse.text(null, { status: 204 }),
      ),
    );
    render(<TypeDeleteDialog type={T} onClose={() => {}} onDeleted={onDeleted} />, { wrapper });
    await waitFor(() => screen.getByPlaceholderText(/请输入完整类型名/));
    expect(screen.getByRole('button', { name: /永久删除/ })).toBeDisabled();
    await user.type(screen.getByPlaceholderText(/请输入完整类型名/), '笔记本');
    expect(screen.getByRole('button', { name: /永久删除/ })).toBeEnabled();
    await user.click(screen.getByRole('button', { name: /永久删除/ }));
    await waitFor(() => expect(onDeleted).toHaveBeenCalled());
  });

  it('refQuery 失败 → 显示错误提示 + 永久删除按钮禁用', async () => {
    server.use(
      http.get('http://localhost:3000/api/assets', () =>
        HttpResponse.json({ detail: 'server error' }, { status: 500 }),
      ),
    );
    render(<TypeDeleteDialog type={T} onClose={() => {}} />, { wrapper });
    await waitFor(() =>
      expect(screen.getByText(/无法确认引用数/)).toBeInTheDocument(),
    );
    expect(screen.getByRole('button', { name: /永久删除/ })).toBeDisabled();
    // confirm input 不应渲染（hasRefs=true 隐藏）
    expect(screen.queryByPlaceholderText(/请输入完整类型名/)).not.toBeInTheDocument();
  });
});
