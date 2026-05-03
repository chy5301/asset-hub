import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

const mutateAsync = vi.fn();

vi.mock('@/api/hooks/assets', async () => {
  const actual = await vi.importActual<typeof import('@/api/hooks/assets')>('@/api/hooks/assets');
  return {
    ...actual,
    useCreateAsset: () => ({ mutateAsync, isPending: false }),
  };
});

const TYPES_FIXTURE = [{
  id: '11111111-1111-4111-8111-111111111111',
  name: '笔记本',
  code_prefix: 'NB',
  description: null,
  custom_fields: [],
  created_at: '2026-05-01T00:00:00Z',
  updated_at: '2026-05-01T00:00:00Z',
}];
const TYPES_QUERY_RESULT = { data: TYPES_FIXTURE, isLoading: false, isError: false } as const;
vi.mock('@/api/hooks/types', () => ({
  useAssetTypesQuery: () => TYPES_QUERY_RESULT,
}));

vi.mock('@tanstack/react-router', () => ({
  useNavigate: () => vi.fn(),
}));

// Calendar 在 jsdom 下交互复杂；mock 成 button，点一下回调固定日期
vi.mock('@/components/ui/calendar', () => ({
  Calendar: ({ onSelect }: { onSelect: (d: Date) => void }) => (
    <button
      type="button"
      data-testid="mock-calendar-pick"
      onClick={() => onSelect(new Date('2026-05-15T00:00:00Z'))}
    >
      mock-pick
    </button>
  ),
}));

// Radix Select 在 jsdom 用 PointerEvent，jsdom 不支持；用原生 <select> 代理
type SelectProps = {
  value?: string;
  onValueChange?: (v: string) => void;
  children?: React.ReactNode;
};
type ItemProps = { value: string; children?: React.ReactNode };
type WrapProps = { children?: React.ReactNode };

vi.mock('@/components/ui/select', () => {
  const Select = ({ value, onValueChange, children }: SelectProps) => (
    <select
      data-testid="mock-select"
      value={value ?? ''}
      onChange={(e) => onValueChange?.(e.target.value)}
    >
      <option value="" disabled>请选择</option>
      {children}
    </select>
  );
  const passthrough = ({ children }: WrapProps) => <>{children}</>;
  const SelectItem = ({ value, children }: ItemProps) => <option value={value}>{children}</option>;
  return {
    Select,
    SelectTrigger: passthrough,
    SelectValue: passthrough,
    SelectContent: passthrough,
    SelectItem,
  };
});

// Radix Popover 在 jsdom 默认不渲染 PopoverContent；展开内容供测试访问
vi.mock('@/components/ui/popover', () => {
  const passthrough = ({ children }: WrapProps) => <>{children}</>;
  return {
    Popover: passthrough,
    PopoverTrigger: passthrough,
    PopoverContent: passthrough,
  };
});

import { AssetCreateForm } from '@/features/assets/form/asset-create-form';

function renderForm() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <AssetCreateForm />
    </QueryClientProvider>,
  );
}

describe('AssetCreateForm acquired_at root-path wiring (§K regression)', () => {
  beforeEach(() => {
    mutateAsync.mockReset();
    mutateAsync.mockResolvedValue({ id: 'created-1' });
  });

  it('用户选日期后提交，mutation body 中 acquired_at 落根路径（不在 custom_data）', async () => {
    const user = userEvent.setup();
    renderForm();

    await user.type(screen.getByLabelText(/资产名/), 'X1 Carbon');
    await user.selectOptions(screen.getByTestId('mock-select'), '11111111-1111-4111-8111-111111111111');
    await user.click(await screen.findByTestId('mock-calendar-pick'));
    await user.click(screen.getByRole('button', { name: /^登记$/ }));

    await waitFor(() => expect(mutateAsync).toHaveBeenCalled());
    const body = mutateAsync.mock.calls[0][0];
    expect(body.acquired_at).toBe('2026-05-15');
    expect(body.custom_data?.acquired_at).toBeUndefined();
    expect(body.name).toBe('X1 Carbon');
    expect(body.type_id).toBe('11111111-1111-4111-8111-111111111111');
  });
});
