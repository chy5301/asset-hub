import { describe, expect, it, beforeEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import {
  COLUMN_LABELS,
  useColumnVisibility,
  type ColumnKey,
} from '@/features/assets/list/column-visibility';

describe('column-visibility · model 列', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('COLUMN_LABELS 含 model = "型号"', () => {
    expect(COLUMN_LABELS.model).toBe('型号');
  });

  it('ColumnKey 联合包含 model（编译期 + 运行期 visible 字典里有 key）', () => {
    const { result } = renderHook(() => useColumnVisibility());
    // visible 字典必须含 model；编译通过 + 运行期 key 存在 = 双保险
    expect('model' in result.current.visible).toBe(true);
  });

  it('默认 visible.model = true（与 serial_number 一档不在 DEFAULT_HIDDEN）', () => {
    const { result } = renderHook(() => useColumnVisibility());
    expect(result.current.visible.model).toBe(true);
  });

  it('toggle(model) 翻转 + 持久化到 localStorage', () => {
    const { result } = renderHook(() => useColumnVisibility());
    expect(result.current.visible.model).toBe(true);

    act(() => result.current.toggle('model' as ColumnKey));
    expect(result.current.visible.model).toBe(false);

    const stored = JSON.parse(localStorage.getItem('asset-hub.list.columns.v2') ?? '{}');
    expect(stored.model).toBe(false);
  });
});
