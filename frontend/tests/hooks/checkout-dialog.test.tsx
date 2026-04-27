import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

// 拦截 mutation hook：本试点关注 RHF/Zod 行为，API 层在 unit/api 测里覆盖。
const mutateAsync = vi.fn();
vi.mock('@/api/hooks/checkouts', () => ({
  useCheckoutMutation: () => ({ mutateAsync, isPending: false }),
}));
// sonner toast 在 jsdom 下无 Toaster 不会渲染，直接 noop 防止意外副作用。
vi.mock('sonner', () => ({ toast: { success: vi.fn(), error: vi.fn() } }));

import { CheckoutDialog } from '@/features/assets/detail/checkout-dialog';

function renderDialog(props: Partial<React.ComponentProps<typeof CheckoutDialog>> = {}) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <CheckoutDialog open onOpenChange={() => {}} assetId="asset-1" {...props} />
    </QueryClientProvider>
  );
}

describe('CheckoutDialog (RHF)', () => {
  beforeEach(() => {
    mutateAsync.mockReset();
    mutateAsync.mockResolvedValue({ id: 'rec-1', holder: '张三' });
  });

  it('blocks submit when holder empty', async () => {
    const user = userEvent.setup();
    renderDialog();
    await user.click(screen.getByRole('button', { name: /确认派发/ }));
    expect(await screen.findByText(/保管人.*必填/)).toBeInTheDocument();
    expect(mutateAsync).not.toHaveBeenCalled();
  });

  it('submits with valid holder', async () => {
    const user = userEvent.setup();
    const onOpenChange = vi.fn();
    renderDialog({ onOpenChange });
    await user.type(screen.getByLabelText(/保管人/), '张三');
    await user.click(screen.getByRole('button', { name: /确认派发/ }));
    await waitFor(() => {
      expect(mutateAsync).toHaveBeenCalledWith({
        assetId: 'asset-1',
        body: { holder: '张三', location: null, note: null },
      });
    });
    await waitFor(() => expect(onOpenChange).toHaveBeenCalledWith(false));
  });
});
