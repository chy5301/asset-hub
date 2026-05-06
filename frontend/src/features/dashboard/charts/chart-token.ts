/**
 * 类型分布 6 槽 chart token 派色 helper.
 *
 * spec §B.fd5: 6 槽色相错位 (240/30/145/80/280/0), 亮度饱和度统一.
 * spec §3.5: 按 type_id 第一个字符 charCode % 6 哈希到固定槽位,
 * 同一 type 每次进看板颜色稳定.
 */

const SLOT_COUNT = 6;

export function typeIdToChartSlot(typeId: string): number {
  if (!typeId.length) return 1;
  return (typeId.charCodeAt(0) % SLOT_COUNT) + 1; // 1..6
}

export function typeIdToChartTokenVar(typeId: string): string {
  return `var(--chart-${typeIdToChartSlot(typeId)})`;
}
