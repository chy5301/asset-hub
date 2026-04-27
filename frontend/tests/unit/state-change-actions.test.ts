import { describe, expect, it } from 'vitest';
import { STATE_CHANGE_ACTIONS, availableStateChanges } from '@/features/assets/detail/state-change-actions';

describe('STATE_CHANGE_ACTIONS', () => {
  it('IDLE allows send_to_maintenance + retire', () => {
    expect(availableStateChanges('IDLE')).toEqual(['send_to_maintenance', 'retire']);
  });
  it('IN_USE allows nothing (must return first)', () => {
    expect(availableStateChanges('IN_USE')).toEqual([]);
  });
  it('MAINTENANCE allows return_from_maintenance + retire', () => {
    expect(availableStateChanges('MAINTENANCE')).toEqual(['return_from_maintenance', 'retire']);
  });
  it('RETIRED allows reactivate', () => {
    expect(availableStateChanges('RETIRED')).toEqual(['reactivate']);
  });

  it('retire confirmBody includes asset name + code', () => {
    const asset = { name: 'X1', asset_code: 'NB-007' } as never;
    expect(STATE_CHANGE_ACTIONS.retire.confirmBody!(asset)).toContain('X1');
    expect(STATE_CHANGE_ACTIONS.retire.confirmBody!(asset)).toContain('NB-007');
  });

  it('only retire/reactivate need confirmation', () => {
    expect(STATE_CHANGE_ACTIONS.send_to_maintenance.needsConfirm).toBe(false);
    expect(STATE_CHANGE_ACTIONS.return_from_maintenance.needsConfirm).toBe(false);
    expect(STATE_CHANGE_ACTIONS.retire.needsConfirm).toBe(true);
    expect(STATE_CHANGE_ACTIONS.reactivate.needsConfirm).toBe(true);
  });
});
