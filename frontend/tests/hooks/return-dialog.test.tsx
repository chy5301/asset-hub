import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

// 拦截 mutation hook：本试点关注 RHF/Zod 行为，API 层在 unit/api 测里覆盖。
const mutateAsync = vi.fn();
vi.mock('@/api/hooks/checkouts', () => ({
  useReturnMutation: () => ({ mutateAsync, isPending: false, isIdle: false }),
}));
vi.mock('sonner', () => ({ toast: { success: vi.fn(), error: vi.fn() } }));

import { ReturnDialog } from '@/features/assets/detail/return-dialog';

const mockCheckout = {
  id: 'rec-1',
  asset_id: 'asset-1',
  holder: '张三',
  location: '工位 A',
  checked_out_at: '2026-04-01T08:00:00Z',
  returned_at: null,
  checkout_note: null,
  return_note: null,
  return_location: null,
  return_receiver: null,
};

function renderDialog(props: Partial<React.ComponentProps<typeof ReturnDialog>> = {}) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <ReturnDialog
        open
        onOpenChange={() => {}}
        assetId="asset-1"
        currentCheckout={mockCheckout}
        {...props}
      />
    </QueryClientProvider>
  );
}

describe('ReturnDialog (RHF + 归还地点/接收人)', () => {
  beforeEach(() => {
    mutateAsync.mockReset();
    mutateAsync.mockResolvedValue({ id: 'rec-1' });
  });

  it('submits with all 3 fields filled', async () => {
    const user = userEvent.setup();
    const onOpenChange = vi.fn();
    renderDialog({ onOpenChange });

    await user.type(screen.getByLabelText(/备注/), '已归还');
    await user.type(screen.getByLabelText(/归还地点/), '仓库A-3排');
    await user.type(screen.getByLabelText(/接收人/), '管理员丁');
    await user.click(screen.getByRole('button', { name: /确认归还/ }));

    await waitFor(() => {
      expect(mutateAsync).toHaveBeenCalledWith({
        assetId: 'asset-1',
        body: {
          note: '已归还',
          return_location: '仓库A-3排',
          return_receiver: '管理员丁',
        },
      });
    });
    await waitFor(() => expect(onOpenChange).toHaveBeenCalledWith(false));
  });

  it('submits with note only (location/receiver empty → null)', async () => {
    const user = userEvent.setup();
    renderDialog();

    await user.type(screen.getByLabelText(/备注/), '仅备注');
    await user.click(screen.getByRole('button', { name: /确认归还/ }));

    await waitFor(() => {
      expect(mutateAsync).toHaveBeenCalledWith({
        assetId: 'asset-1',
        body: {
          note: '仅备注',
          return_location: null,
          return_receiver: null,
        },
      });
    });
  });
});
