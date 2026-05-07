import { differenceInCalendarDays, format, parseISO } from "date-fns";

export function formatDateTime(iso: string): string {
  return format(parseISO(iso), "yyyy-MM-dd HH:mm");
}

export function formatDate(iso: string): string {
  return format(parseISO(iso), "yyyy-MM-dd");
}

/** 按本地日历日返"今天"/"昨天"/"N 天前"。与 formatDate 同时区语义对齐
 *  （都用 date-fns 本地时区），timeline 卡上 "yyyy-MM-dd · N 天前" 拼接不会跨时区矛盾。 */
export function formatRelative(iso: string, now: Date = new Date()): string {
  const days = Math.max(0, differenceInCalendarDays(now, parseISO(iso)));
  if (days === 0) return "今天";
  if (days === 1) return "昨天";
  return `${days} 天前`;
}
