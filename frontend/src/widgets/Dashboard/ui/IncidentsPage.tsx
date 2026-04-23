import { useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import { Search, X } from "lucide-react";
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
          <h1 className="text-2xl font-bold text-slate-900">Инциденты</h1>
          <p className="mt-1 text-sm text-slate-500">
            {data ? `${data.count} инцидентов` : "загрузка…"}
            {isFetching && " · обновление…"}
          </p>
        </div>
      </div>

      <div className="mb-4 flex flex-wrap items-center gap-3 rounded-xl border border-slate-200 bg-white p-3 shadow-sm">
        <div className="relative flex-1 min-w-[240px]">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Поиск по title / fingerprint"
            className="h-9 w-full rounded-lg border border-slate-200 bg-white pl-9 pr-8 text-sm outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-100"
          />
          {search && (
            <button
              onClick={() => setSearch("")}
              className="absolute right-2 top-1/2 -translate-y-1/2 rounded p-1 text-slate-400 hover:bg-slate-100"
            >
              <X className="h-3 w-3" />
            </button>
          )}
        </div>

        <div className="flex items-center gap-1">
          <span className="text-xs font-medium text-slate-500">Статус:</span>
          {STATUSES.map((st) => (
            <button
              key={st}
              onClick={() => setStatus(st)}
              className={cn(
                "rounded-md px-2.5 py-1 text-xs font-medium transition",
                status === st
                  ? "bg-slate-900 text-white"
                  : "text-slate-600 hover:bg-slate-100"
              )}
            >
              {st === "all" ? "все" : statusLabel[st]}
            </button>
          ))}
        </div>

        <div className="flex items-center gap-1">
          <span className="text-xs font-medium text-slate-500">Severity:</span>
          {SEVERITIES.map((sv) => (
            <button
              key={sv}
              onClick={() => setSeverity(sv)}
              className={cn(
                "rounded-md px-2.5 py-1 text-xs font-medium transition",
                severity === sv
                  ? "bg-slate-900 text-white"
                  : "text-slate-600 hover:bg-slate-100"
              )}
            >
              {sv}
            </button>
          ))}
        </div>
      </div>

      <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
        <table className="w-full">
          <thead className="bg-slate-50 text-xs font-semibold uppercase tracking-wide text-slate-500">
            <tr>
              <th className="px-4 py-3 text-left">Инцидент</th>
              <th className="px-4 py-3 text-left">Сервис</th>
              <th className="px-4 py-3 text-left">Root cause</th>
              <th className="px-4 py-3 text-right">Impact</th>
              <th className="px-4 py-3 text-right">Burn 1h</th>
              <th className="px-4 py-3 text-left">Открыт</th>
              <th className="px-4 py-3 text-left">Статус</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {isLoading ? (
              <tr>
                <td colSpan={7} className="py-12 text-center text-sm text-slate-400">
                  загрузка…
                </td>
              </tr>
            ) : items.length === 0 ? (
              <tr>
                <td colSpan={7} className="py-12 text-center text-sm text-slate-400">
                  Инциденты не найдены
                </td>
              </tr>
            ) : (
              items.map((inc) => (
                <tr
                  key={inc.incident_id}
                  onClick={() => dispatch(selectIncident(inc.incident_id))}
                  className="cursor-pointer transition hover:bg-slate-50"
                >
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <span
                        className={cn(
                          "rounded-md px-2 py-0.5 text-[10px] font-semibold uppercase",
                          severityColors[inc.severity]
                        )}
                      >
                        {inc.severity}
                      </span>
                      <span className="text-sm font-medium text-slate-900">
                        {truncate(inc.title, 60)}
                      </span>
                    </div>
                    <div className="mt-1 font-mono text-[10px] text-slate-400">
                      {inc.fingerprint.slice(0, 16)}
                    </div>
                  </td>
                  <td className="px-4 py-3 text-sm text-slate-700">
                    <div>{inc.service}</div>
                    <div className="text-[11px] text-slate-400">
                      {inc.environment} · {inc.category}
                    </div>
                  </td>
                  <td className="px-4 py-3 text-sm text-slate-700">
                    {inc.root_cause_service || "—"}
                  </td>
                  <td className="px-4 py-3 text-right font-mono text-sm text-slate-900">
                    {formatNumber(inc.impact_score, 2)}
                  </td>
                  <td className="px-4 py-3 text-right font-mono text-sm">
                    <span
                      className={cn(
                        "rounded px-1.5 py-0.5",
                        inc.burn_rate_1h > 14.4
                          ? "bg-red-50 text-red-700"
                          : inc.burn_rate_1h > 6
                          ? "bg-amber-50 text-amber-700"
                          : "text-slate-700"
                      )}
                    >
                      {formatNumber(inc.burn_rate_1h, 1)}×
                    </span>
                  </td>
                  <td className="px-4 py-3 text-xs text-slate-500">
                    {formatRelativeTime(inc.opened_at)}
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={cn(
                        "rounded-md px-2 py-0.5 text-[11px] font-medium",
                        statusColors[inc.status]
                      )}
                    >
                      {statusLabel[inc.status]}
                    </span>
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
