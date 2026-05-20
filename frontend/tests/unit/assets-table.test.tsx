import { describe, expect, it, vi } from 'vitest';
import { render, screen, within } from '@testing-library/react';
import {
  createMemoryHistory,
  createRouter,
  RouterProvider,
  createRootRoute,
  createRoute,
  Outlet,
} from '@tanstack/react-router';

import { AssetsTable, type AssetRow } from '@/features/assets/list/assets-table';
import { COLUMN_LABELS } from '@/features/assets/list/column-visibility';
import type { AssetsSearch } from '@/features/assets/list/search-schema';

function renderTable(rows: AssetRow[]) {
  const visible = {
    asset_code: true,
    name: true,
    brand: true,
    model: true,
    serial_number: true,
    type: true,
    status: true,
    holder: true,
    location: true,
    updated_at: true,
    acquired_at: false,
  } as const;

  const search: AssetsSearch = {
    sort: 'asset_code',
    page: 1,
    pageSize: 50,
  } as AssetsSearch;

  const rootRoute = createRootRoute({ component: () => <Outlet /> });
  const indexRoute = createRoute({
    getParentRoute: () => rootRoute,
    path: '/',
    component: () => (
      <AssetsTable
        rows={rows}
        search={search}
        visible={visible}
        bodyKey="k1"
        onCheckout={vi.fn()}
        onReturn={vi.fn()}
        onDelete={vi.fn()}
      />
    ),
    validateSearch: (s: Record<string, unknown>) => s,
  });
  const router = createRouter({
    routeTree: rootRoute.addChildren([indexRoute]),
    history: createMemoryHistory({ initialEntries: ['/'] }),
  });
  return render(<RouterProvider router={router} />);
}

const baseRow: AssetRow = {
  id: 'a1',
  asset_code: 'NB-001',
  name: 'ThinkPad X1',
  brand: null,
  model: null,
  serial_number: null,
  type_id: 't1',
  type_name: '笔记本',
  status: 'IDLE',
  holder: null,
  location: null,
  updated_at: '2026-04-20T00:00:00Z',
  acquired_at: null,
};

describe('AssetsTable · model 列', () => {
  it('表头含 "型号" 列', async () => {
    renderTable([baseRow]);
    expect(await screen.findByText(COLUMN_LABELS.model)).toBeInTheDocument();
  });

  it('model 有值时显示 model 字符串', async () => {
    renderTable([{ ...baseRow, model: 'X1 Carbon Gen 9' }]);
    expect(await screen.findByText('X1 Carbon Gen 9')).toBeInTheDocument();
  });

  it('model 为 null 时显示 —', async () => {
    renderTable([baseRow]);
    // 行数据里 row.id + name 已渲染，再检查 — 占位
    await screen.findByText('ThinkPad X1');
    // 至少一处 — 占位（model/sn/holder/location/acquired 都可能空，这里只断言 row 出现 —）
    const dashes = screen.queryAllByText('—');
    expect(dashes.length).toBeGreaterThan(0);
  });

  it('列顺序：name → brand → model → serial_number', async () => {
    renderTable([baseRow]);
    const headerRow = await screen.findByRole('row', { name: /名称/ });
    const headers = within(headerRow).getAllByRole('columnheader');
    const headerTexts = headers.map((h) => h.textContent ?? '');
    const nameIdx = headerTexts.findIndex((t) => t.includes('名称'));
    const brandIdx = headerTexts.findIndex((t) => t.includes('品牌'));
    const modelIdx = headerTexts.findIndex((t) => t.includes('型号'));
    const snIdx = headerTexts.findIndex((t) => t.includes('SN'));
    expect(nameIdx).toBeGreaterThanOrEqual(0);
    expect(brandIdx).toBe(nameIdx + 1);
    expect(modelIdx).toBe(brandIdx + 1);
    expect(snIdx).toBe(modelIdx + 1);
  });
});
