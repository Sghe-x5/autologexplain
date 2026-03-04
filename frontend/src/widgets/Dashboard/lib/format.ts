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
  critical: "bg-rose-500/10 text-rose-300 border border-rose-500/30",
  error: "bg-orange-500/10 text-orange-300 border border-orange-500/30",
  warning: "bg-amber-500/10 text-amber-300 border border-amber-500/30",
  info: "bg-sky-500/10 text-sky-300 border border-sky-500/30",
  debug: "bg-zinc-500/10 text-zinc-400 border border-zinc-500/30",
};

export const statusColors: Record<IncidentStatus, string> = {
  open: "bg-rose-500/10 text-rose-300 border border-rose-500/30",
  acknowledged: "bg-amber-500/10 text-amber-300 border border-amber-500/30",
  mitigated: "bg-sky-500/10 text-sky-300 border border-sky-500/30",
  resolved: "bg-emerald-500/10 text-emerald-300 border border-emerald-500/30",
  reopened: "bg-violet-500/10 text-violet-300 border border-violet-500/30",
};

export const alertLevelColors: Record<AlertLevel, string> = {
  page: "bg-rose-500/10 text-rose-300 border border-rose-500/30",
  ticket: "bg-orange-500/10 text-orange-300 border border-orange-500/30",
  warning: "bg-amber-500/10 text-amber-300 border border-amber-500/30",
  none: "bg-emerald-500/10 text-emerald-300 border border-emerald-500/30",
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
