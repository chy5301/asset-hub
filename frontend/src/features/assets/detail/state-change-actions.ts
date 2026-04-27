import type { components } from '@/api/generated/schema';

type AssetStatus = components['schemas']['AssetStatus'];
type AssetRead = components['schemas']['AssetRead'];

export type StateChangeKey = 'send_to_maintenance' | 'return_from_maintenance' | 'retire' | 'reactivate';

export interface StateChangeAction {
  fromStatuses: AssetStatus[];
  toStatus: AssetStatus;
  verb: string;
  inProgressVerb: string;
  /** 是否需要 AlertDialog 二次确认 */
  needsConfirm: boolean;
  /** 仅 needsConfirm=true 用 */
  confirmTitle?: string;
  confirmBody?: (a: AssetRead) => string;
  confirmAction?: string;
}

export const STATE_CHANGE_ACTIONS: Record<StateChangeKey, StateChangeAction> = {
  send_to_maintenance: {
    fromStatuses: ['IDLE'],
    toStatus: 'MAINTENANCE',
    verb: '送修',
    inProgressVerb: '送修中…',
    needsConfirm: false,
  },
  return_from_maintenance: {
    fromStatuses: ['MAINTENANCE'],
    toStatus: 'IDLE',
    verb: '修好回库',
    inProgressVerb: '回库中…',
    needsConfirm: false,
  },
  retire: {
    fromStatuses: ['IDLE', 'MAINTENANCE'],
    toStatus: 'RETIRED',
    verb: '退役',
    inProgressVerb: '退役中…',
    needsConfirm: true,
    confirmTitle: '退役这台资产？',
    confirmBody: (a) => `${a.name} · ${a.asset_code} 将标记为退役。退役后默认仍在列表中显示，可通过「重新启用」复活。`,
    confirmAction: '确认退役',
  },
  reactivate: {
    fromStatuses: ['RETIRED'],
    toStatus: 'IDLE',
    verb: '重新启用',
    inProgressVerb: '启用中…',
    needsConfirm: true,
    confirmTitle: '重新启用这台资产？',
    confirmBody: (a) => `${a.name} · ${a.asset_code} 将从退役状态恢复为闲置。`,
    confirmAction: '确认启用',
  },
};

/** 给定当前 status，返回菜单中应显示的所有 state change keys（顺序固定）。 */
export function availableStateChanges(status: AssetStatus): StateChangeKey[] {
  return (Object.entries(STATE_CHANGE_ACTIONS) as [StateChangeKey, StateChangeAction][])
    .filter(([, action]) => action.fromStatuses.includes(status))
    .map(([key]) => key);
}
