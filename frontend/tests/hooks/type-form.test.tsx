import { describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { setupServer } from 'msw/node';
import { http, HttpResponse } from 'msw';
import { TypeForm } from '@/features/types/form/type-form';

type MswServer = ReturnType<typeof setupServer>;
const server = (globalThis as unknown as { __mswServer: MswServer }).__mswServer;

const wrapper = ({ children }: { children: React.ReactNode }) => {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
};

describe('TypeForm', () => {
  it('create 模式提交 POST /api/types', async () => {
    const user = userEvent.setup();
    let body: unknown;
    server.use(
      http.post('http://localhost:3000/api/types', async ({ request }) => {
        body = await request.json();
        return HttpResponse.json(
          { id: 'new-id', name: '笔记本', code_prefix: 'NB', description: null, custom_fields: [], created_at: '', updated_at: '' },
          { status: 201 },
        );
      }),
    );
    const onSuccess = vi.fn();
    render(<TypeForm mode="create" onSuccess={onSuccess} />, { wrapper });
    await user.type(screen.getByLabelText(/name/i), '笔记本');
    await user.type(screen.getByLabelText(/code_prefix/i), 'NB');
    await user.click(screen.getByRole('button', { name: /保存/ }));
    await waitFor(() => expect(onSuccess).toHaveBeenCalled());
    expect((body as { name: string }).name).toBe('笔记本');
    expect((body as { code_prefix: string }).code_prefix).toBe('NB');
  });

  it('edit 模式 code_prefix readOnly 不进 PATCH body', async () => {
    const user = userEvent.setup();
    let patchBody: unknown;
    server.use(
      http.patch('http://localhost:3000/api/types/abc', async ({ request }) => {
        patchBody = await request.json();
        return HttpResponse.json({
          id: 'abc',
          name: 'New',
          code_prefix: 'NB',
          description: null,
          custom_fields: [],
          created_at: '',
          updated_at: '',
        });
      }),
    );
    render(
      <TypeForm
        mode="edit"
        initial={{
          id: 'abc',
          name: 'Old',
          code_prefix: 'NB',
          description: null,
          custom_fields: [],
          created_at: '',
          updated_at: '',
        }}
        onSuccess={() => {}}
      />,
      { wrapper },
    );
    const nameInput = screen.getByLabelText(/name/i);
    await user.clear(nameInput);
    await user.type(nameInput, 'New');
    await user.click(screen.getByRole('button', { name: /保存/ }));
    await waitFor(() => expect(patchBody).toBeDefined());
    expect((patchBody as { code_prefix?: string }).code_prefix).toBeUndefined();
    expect((patchBody as { name?: string }).name).toBe('New');
  });

  it('DuplicateError 设字段级 setError(code_prefix)', async () => {
    const user = userEvent.setup();
    server.use(
      http.post('http://localhost:3000/api/types', () =>
        HttpResponse.json({ detail: 'code_prefix 已存在: NB' }, { status: 409 }),
      ),
    );
    render(<TypeForm mode="create" onSuccess={() => {}} />, { wrapper });
    await user.type(screen.getByLabelText(/name/i), 'X');
    await user.type(screen.getByLabelText(/code_prefix/i), 'NB');
    await user.click(screen.getByRole('button', { name: /保存/ }));
    await waitFor(() =>
      expect(screen.getByText(/code_prefix 已存在/)).toBeInTheDocument(),
    );
  });
});
