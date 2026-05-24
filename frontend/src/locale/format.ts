const WEEKDAYS = ["周日", "周一", "周二", "周三", "周四", "周五", "周六"] as const;

export function formatDayHeader(date: Date): string {
  const iso = date.toISOString().slice(0, 10);
  return `${iso} · ${WEEKDAYS[date.getDay()]}`;
}
