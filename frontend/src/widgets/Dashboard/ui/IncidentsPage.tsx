import { useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import { Search, X, ChevronRight, ArrowUpDown, Sparkles } from "lucide-react";
import { useListIncidentsQuery } from "@/api";
import type {
  IncidentSeverity,
  IncidentStatus,
} from "@/api/incidentsApi";
import type { AppDispatch, RootState } from "@/lib/store";
import { selectIncident } from "@/widgets/Dashboard/model/viewSlice";
import {
  formatRelativeTime,
  formatNumber,
  severityColors,
  statusColors,
  statusLabel,
  truncate,
} from "@/widgets/Dashboard/lib/format";
import { cn } from "@/lib/utils";
import { IncidentDetails } from "./IncidentDetails";

const STATUSES: (IncidentStatus | "all")[] = [
  "all",
  "open",
  "acknowledged",
  "mitigated",
  "resolved",
  "reopened",
];
const SEVERITIES: (IncidentSeverity | "all")[] = [
  "all",
  "critical",
  "error",
  "warning",
  "info",
];

// Mini burn-rate bar with number
function BurnRateCell({ value }: { value: number }) {
  const stroke =
    value > 14.4 ? "#f43f5e" : value > 6 ? "#f59e0b" : "#64748b";
  const fill =
    value > 14.4 ? "rgba(244,63,94,0.15)" : value > 6 ? "rgba(245,158,11,0.15)" : "rgba(100,116,139,0.1)";
  const textColor =
    value > 14.4 ? "text-rose-400" : value > 6 ? "text-amber-400" : "text-zinc-400";
  // 10 semi-random points from the value — stable per value
  const seed = Math.round(value * 10);
  const points = Array.from({ length: 10 }, (_, i) => {
    const n = ((seed * (i + 1) * 37) % 100) / 100;
    const base = Math.min(0.9, value / 200 + 0.1);
    return Math.max(0.1, base * (0.7 + n * 0.6));
  });
  const step = 64 / 9;
  const path = points
    .map((v, i) => `${i === 0 ? "M" : "L"} ${(i * step).toFixed(1)} ${(24 - v * 24).toFixed(1)}`)
    .join(" ");
  return (
    <div className="flex items-center justify-end gap-2">
      <svg viewBox="0 0 64 24" className="h-5 w-16" preserveAspectRatio="none">
        <path d={`${path} L 64 24 L 0 24 Z`} fill={fill} />
        <path d={path} stroke={stroke} strokeWidth="1.3" fill="none" strokeLinecap="round" />
      </svg>
      <span className={cn("font-mono text-sm tabular-nums", textColor)}>
        {formatNumber(value, 1)}x
      </span>
    </div>
  );
}

export const IncidentsPage = () => {
  const dispatch = useDispatch<AppDispatch>();
  const selectedId = useSelector(
    (s: RootState) => s.dashboardView.selectedIncidentId
  );

  const [status, setStatus] = useState<IncidentStatus | "all">("all");
  const [severity, setSeverity] = useState<IncidentSeverity | "all">("all");
  const [search, setSearch] = useState("");

  const { data, isLoading, isFetching } = useListIncidentsQuery({
    limit: 200,
    ...(status !== "all" ? { status } : {}),
    ...(severity !== "all" ? { severity } : {}),
    ...(search ? { q: search } : {}),
  });

  const items = data?.items ?? [];

  if (selectedId) {
    return (
      <IncidentDetails
        key={selectedId}
        incidentId={selectedId}
        onBack={() => dispatch(selectIncident(null))}
      />
    );
  }

  return (
    <div className="mx-auto max-w-7xl px-6 py-8">
      <div className="mb-6 flex items-start justify-between">
        <div>
          <h1 className="flex items-center gap-3 text-2xl font-bold text-zinc-50">
            <span className="inline-block h-5 w-1 rounded-sm bg-violet-500" />
            Инциденты
            {data && (
              <span className="rounded-md border border-violet-500/30 bg-violet-500/10 px-2 py-0.5 text-xs font-semibold text-violet-300">
                {data.count} инцидентов
              </span>
            )}
          </h1>
          {isFetching && !isLoading && (
            <p className="mt-1 text-xs text-zinc-500">обновление…</p>
          )}
        </div>
      </div>

      <div className="mb-4 flex flex-wrap items-center gap-3 rounded-xl border border-zinc-800/60 bg-zinc-900/40 p-3 backdrop-blur">
        <div className="relative min-w-[240px] flex-1">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-500" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Поиск по title / fingerprint"
            className="h-9 w-full rounded-lg border border-zinc-800 bg-zinc-950/60 pl-9 pr-14 font-mono text-sm text-zinc-200 placeholder:text-zinc-600 outline-none transition focus:border-violet-500/50 focus:ring-2 focus:ring-violet-500/20"
          />
          {search ? (
            <button
              onClick={() => setSearch("")}
              className="absolute right-2 top-1/2 -translate-y-1/2 rounded p-1 text-zinc-500 hover:bg-zinc-800 hover:text-zinc-300"
            >
              <X className="h-3 w-3" />
            </button>
          ) : (
            <kbd className="absolute right-2 top-1/2 -translate-y-1/2 rounded border border-zinc-700 bg-zinc-800/60 px-1.5 py-0.5 font-mono text-[10px] text-zinc-500">
              ⌘K
            </kbd>
          )}
        </div>

        <div className="flex items-center gap-1">
          <span className="text-[10px] font-semibold uppercase tracking-wider text-zinc-500">
            Статус:
          </span>
          {STATUSES.map((st) => (
            <button
              key={st}
              onClick={() => setStatus(st)}
              className={cn(
                "rounded-md px-2.5 py-1 text-xs font-medium transition",
                status === st
                  ? "bg-zinc-800 text-zinc-50 ring-1 ring-zinc-700"
                  : "text-zinc-500 hover:bg-zinc-900 hover:text-zinc-300"
              )}
            >
              {st === "all" ? "все" : statusLabel[st].toLowerCase()}
            </button>
          ))}
        </div>

        <div className="flex items-center gap-1">
          <span className="text-[10px] font-semibold uppercase tracking-wider text-zinc-500">
            Severity:
          </span>
          {SEVERITIES.map((sv) => (
            <button
              key={sv}
              onClick={() => setSeverity(sv)}
              className={cn(
                "rounded-md px-2.5 py-1 text-xs font-medium uppercase tracking-wide transition",
                severity === sv
                  ? sv === "critical"
                    ? "bg-rose-500/15 text-rose-300 ring-1 ring-rose-500/40"
                    : sv === "error"
                    ? "bg-orange-500/15 text-orange-300 ring-1 ring-orange-500/40"
                    : sv === "warning"
                    ? "bg-amber-500/15 text-amber-300 ring-1 ring-amber-500/40"
                    : sv === "info"
                    ? "bg-sky-500/15 text-sky-300 ring-1 ring-sky-500/40"
                    : "bg-zinc-800 text-zinc-50 ring-1 ring-zinc-700"
                  : "text-zinc-500 hover:bg-zinc-900 hover:text-zinc-300"
              )}
            >
              {sv}
            </button>
          ))}
        </div>
      </div>

      <div className="overflow-hidden rounded-xl border border-zinc-800/60 bg-zinc-900/40 backdrop-blur">
        <table className="w-full">
          <thead className="bg-zinc-950/60 text-[10px] font-semibold uppercase tracking-wider text-zinc-500">
            <tr>
              <th className="px-4 py-3 text-left">Инцидент</th>
              <th className="px-4 py-3 text-left">Сервис</th>
              <th className="px-4 py-3 text-left">Root cause</th>
              <th className="px-4 py-3 text-right">
                <span className="inline-flex items-center gap-1">
                  Impact <ArrowUpDown className="h-3 w-3" />
                </span>
              </th>
              <th className="px-4 py-3 text-right">Burn 1h</th>
              <th className="px-4 py-3 text-left">Открыт</th>
              <th className="px-4 py-3 text-left">Статус</th>
              <th className="w-8 px-2 py-3"></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-zinc-800/60">
            {isLoading ? (
              <tr>
                <td colSpan={8} className="py-12 text-center text-sm text-zinc-600">
                  загрузка…
                </td>
              </tr>
            ) : items.length === 0 ? (
              <tr>
                <td colSpan={8} className="py-12 text-center text-sm text-zinc-600">
                  Инциденты не найдены
                </td>
              </tr>
            ) : (
              items.map((inc) => (
                <tr
                  key={inc.incident_id}
                  onClick={() => dispatch(selectIncident(inc.incident_id))}
                  className="group cursor-pointer transition hover:bg-zinc-900/60"
                >
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <span
                        className={cn(
                          "rounded px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-wider",
                          severityColors[inc.severity]
                        )}
                      >
                        ● {inc.severity}
                      </span>
                      <span className="text-sm font-medium text-zinc-100">
                        {truncate(inc.title, 60)}
                      </span>
                    </div>
                    <div className="mt-1 font-mono text-[10px] text-zinc-600">
                      {inc.fingerprint.slice(0, 16)}
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <code className="rounded border border-zinc-800 bg-zinc-950/60 px-1.5 py-0.5 font-mono text-[11px] text-zinc-300">
                      {inc.service}
                    </code>
                    <div className="mt-1 font-mono text-[10px] text-zinc-600">
                      {inc.environment} · {inc.category}
                    </div>
                  </td>
                  <td className="px-4 py-3 text-sm">
                    {inc.root_cause_service ? (
                      <span className="inline-flex items-center gap-1.5 font-mono text-violet-400">
                        <Sparkles className="h-3 w-3" />
                        {inc.root_cause_service}
                      </span>
                    ) : (
                      <span className="text-zinc-600">—</span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-right font-mono text-sm tabular-nums text-zinc-100">
                    {formatNumber(inc.impact_score, 2)}
                  </td>
                  <td className="px-4 py-3">
                    <BurnRateCell value={inc.burn_rate_1h} />
                  </td>
                  <td className="px-4 py-3 text-xs text-zinc-500">
                    {formatRelativeTime(inc.opened_at)}
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={cn(
                        "rounded px-2 py-0.5 text-[10px] font-medium uppercase tracking-wider",
                        statusColors[inc.status]
                      )}
                    >
                      {statusLabel[inc.status].toLowerCase()}
                    </span>
                  </td>
                  <td className="px-2 py-3 text-right text-zinc-600 transition group-hover:text-violet-400">
                    <ChevronRight className="h-4 w-4" />
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};
