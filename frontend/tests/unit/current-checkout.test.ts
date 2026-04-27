import { describe, expect, it } from 'vitest';
import { deriveCurrentCheckout } from '@/features/assets/detail/current-checkout';

// deriveCurrentCheckout(history, currentCheckoutId): CheckoutRead | null
// 用 asset.current_checkout_id 直接 find by id；history 为空或 id 为 null 时返回 null。

describe('deriveCurrentCheckout', () => {
  it('returns null for undefined history', () => {
    expect(deriveCurrentCheckout(undefined, 'b')).toBeNull();
  });

  it('returns null for empty history', () => {
    expect(deriveCurrentCheckout([], 'b')).toBeNull();
  });

  it('returns null when current_checkout_id is null', () => {
    const history = [
      { id: 'a', returned_at: '2025-01-01T00:00:00Z' },
      { id: 'b', returned_at: null },
    ];
    expect(deriveCurrentCheckout(history as never, null)).toBeNull();
    expect(deriveCurrentCheckout(history as never, undefined)).toBeNull();
  });

  it('returns the record matching current_checkout_id', () => {
    const active = { id: 'b', returned_at: null };
    const history = [
      { id: 'a', returned_at: '2025-01-01T00:00:00Z' },
      active,
    ];
    expect(deriveCurrentCheckout(history as never, 'b')).toBe(active);
  });

  it('returns null when current_checkout_id has no match (stale state)', () => {
    const history = [{ id: 'a', returned_at: '2025-01-01T00:00:00Z' }];
    expect(deriveCurrentCheckout(history as never, 'missing')).toBeNull();
  });
});
