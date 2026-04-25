import { format, parseISO } from "date-fns";

export function formatDateTime(iso: string): string {
  return format(parseISO(iso), "yyyy-MM-dd HH:mm");
}

export function formatDate(iso: string): string {
  return format(parseISO(iso), "yyyy-MM-dd");
}
