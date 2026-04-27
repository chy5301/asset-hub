import { describe, expect, it } from 'vitest';
import { deriveCurrentCheckout } from '@/features/assets/detail/current-checkout';

// 实际签名（current-checkout.ts）：
//   deriveCurrentCheckout(history: CheckoutRead[] | undefined): CheckoutRead | null
// 实现策略：在 history 中 .find(c => c.returned_at === null) ?? null
// 因此对"多个 active"场景，返回的是数组中**第一个** returned_at === null 的记录。

describe('deriveCurrentCheckout', () => {
  it('returns null for undefined history', () => {
    expect(deriveCurrentCheckout(undefined)).toBeNull();
  });

  it('returns null for empty history', () => {
    expect(deriveCurrentCheckout([])).toBeNull();
  });

  it('returns null when all records are returned', () => {
    const history = [
      { id: 'a', returned_at: '2025-01-01T00:00:00Z' },
      { id: 'b', returned_at: '2025-02-01T00:00:00Z' },
    ];
    expect(deriveCurrentCheckout(history as never)).toBeNull();
  });

  it('returns the single active record (returned_at === null)', () => {
    const active = { id: 'b', returned_at: null };
    const history = [
      { id: 'a', returned_at: '2025-01-01T00:00:00Z' },
      active,
    ];
    expect(deriveCurrentCheckout(history as never)).toBe(active);
  });

  it('returns the first active record when multiple active (anomaly safety, find() short-circuits)', () => {
    const first = { id: 'a', returned_at: null, checked_out_at: '2025-01-01T00:00:00Z' };
    const second = { id: 'b', returned_at: null, checked_out_at: '2025-02-01T00:00:00Z' };
    const result = deriveCurrentCheckout([first, second] as never);
    // service 层不变量保证最多 1 条 active；这里描述 .find() 的实际行为
    expect(result).toBe(first);
  });
});
