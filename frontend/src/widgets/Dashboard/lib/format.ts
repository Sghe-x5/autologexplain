import type { AlertLevel } from "@/api/rcaApi";
import type { IncidentSeverity, IncidentStatus } from "@/api/incidentsApi";

export function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  try {
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return iso;
    return d.toLocaleString("ru-RU", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return iso ?? "—";
  }
}

export function formatRelativeTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  try {
    const d = new Date(iso);
    const diffMs = Date.now() - d.getTime();
    const diffMin = Math.floor(diffMs / 60000);
    if (diffMin < 1) return "только что";
    if (diffMin < 60) return `${diffMin} мин назад`;
    const diffHr = Math.floor(diffMin / 60);
    if (diffHr < 24) return `${diffHr} ч назад`;
    const diffDay = Math.floor(diffHr / 24);
    return `${diffDay} дн назад`;
  } catch {
    return iso ?? "—";
  }
}

export const severityColors: Record<IncidentSeverity, string> = {
  critical: "bg-red-100 text-red-800 border border-red-200",
  error: "bg-orange-100 text-orange-800 border border-orange-200",
  warning: "bg-amber-100 text-amber-800 border border-amber-200",
  info: "bg-blue-50 text-blue-700 border border-blue-100",
  debug: "bg-slate-100 text-slate-600 border border-slate-200",
};

export const statusColors: Record<IncidentStatus, string> = {
  open: "bg-red-50 text-red-700 border border-red-200",
  acknowledged: "bg-amber-50 text-amber-700 border border-amber-200",
  mitigated: "bg-blue-50 text-blue-700 border border-blue-200",
  resolved: "bg-emerald-50 text-emerald-700 border border-emerald-200",
  reopened: "bg-purple-50 text-purple-700 border border-purple-200",
};

export const alertLevelColors: Record<AlertLevel, string> = {
  page: "bg-red-100 text-red-800 border border-red-200",
  ticket: "bg-orange-100 text-orange-800 border border-orange-200",
  warning: "bg-amber-100 text-amber-800 border border-amber-200",
  none: "bg-emerald-50 text-emerald-700 border border-emerald-200",
};

export const alertLevelLabel: Record<AlertLevel, string> = {
  page: "PAGE",
  ticket: "TICKET",
  warning: "WARN",
  none: "OK",
};

export const statusLabel: Record<IncidentStatus, string> = {
  open: "Открыт",
  acknowledged: "Принят",
  mitigated: "Подавлен",
  resolved: "Решён",
  reopened: "Переоткрыт",
};

export function truncate(s: string, n = 80): string {
  return s.length > n ? s.slice(0, n - 1) + "…" : s;
}

export function formatNumber(n: number, digits = 2): string {
  if (!Number.isFinite(n)) return "—";
  return n.toFixed(digits);
}
