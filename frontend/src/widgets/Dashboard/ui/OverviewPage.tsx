import { useMemo } from "react";
import { useDispatch } from "react-redux";
import {
  AlertTriangle,
  Activity,
  Gauge,
  ArrowUpRight,
  TrendingUp,
  FileText,
} from "lucide-react";
import {
  useListIncidentsQuery,
  useGetSloStatusQuery,
  useGetLogTemplatesQuery,
} from "@/api";
import type { AppDispatch } from "@/lib/store";
import { setView, selectIncident } from "@/widgets/Dashboard/model/viewSlice";
import {
  alertLevelColors,
  alertLevelLabel,
  formatNumber,
  formatRelativeTime,
  severityColors,
  statusLabel,
  statusColors,
  truncate,
} from "@/widgets/Dashboard/lib/format";
import { cn } from "@/lib/utils";

function Kpi({
  icon,
  label,
  value,
  caption,
  tone = "slate",
}: {
  icon: React.ReactNode;
  label: string;
  value: React.ReactNode;
  caption?: string;
  tone?: "slate" | "red" | "amber" | "emerald" | "blue";
}) {
  const tones: Record<typeof tone, string> = {
    slate: "from-slate-50 to-white border-slate-200",
    red: "from-red-50 to-white border-red-200",
    amber: "from-amber-50 to-white border-amber-200",
    emerald: "from-emerald-50 to-white border-emerald-200",
    blue: "from-blue-50 to-white border-blue-200",
  };
  const iconTones: Record<typeof tone, string> = {
    slate: "bg-slate-100 text-slate-600",
    red: "bg-red-100 text-red-700",
    amber: "bg-amber-100 text-amber-700",
    emerald: "bg-emerald-100 text-emerald-700",
    blue: "bg-blue-100 text-blue-700",
  };
  return (
    <div
      className={cn(
        "rounded-2xl border bg-gradient-to-br p-5 shadow-sm",
        tones[tone]
      )}
    >
      <div className="flex items-start justify-between">
        <div
          className={cn(
            "flex h-10 w-10 items-center justify-center rounded-xl",
            iconTones[tone]
          )}
        >
          {icon}
        </div>
      </div>
      <div className="mt-4 text-3xl font-bold text-slate-900">{value}</div>
      <div className="mt-1 text-sm font-medium text-slate-700">{label}</div>
      {caption && (
        <div className="mt-0.5 text-xs text-slate-500">{caption}</div>
      )}
    </div>
  );
}

export const OverviewPage = () => {
  const dispatch = useDispatch<AppDispatch>();
  const incidents = useListIncidentsQuery({ limit: 100 });
  const slo = useGetSloStatusQuery({ hours: 4 });
  const templates = useGetLogTemplatesQuery({ hours: 4, top_n: 5 });

  const active = useMemo(
    () =>
      (incidents.data?.items ?? []).filter(
        (i) => i.status !== "resolved"
      ),
    [incidents.data]
  );
  const critical = active.filter((i) => i.severity === "critical").length;
  const pageAlerts = (slo.data?.services ?? []).filter(
    (s) => s.alert_level === "page"
  ).length;
  const healthyServices = (slo.data?.services ?? []).filter(
    (s) => s.alert_level === "none"
  ).length;

  const topIncidents = useMemo(
    () =>
      [...(incidents.data?.items ?? [])]
        .sort((a, b) => (b.impact_score ?? 0) - (a.impact_score ?? 0))
        .slice(0, 5),
    [incidents.data]
  );

  return (
    <div className="mx-auto max-w-7xl px-6 py-8">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-slate-900">Обзор системы</h1>
        <p className="mt-1 text-sm text-slate-500">
          Текущее состояние инцидентов, SLO и топ-шаблоны ошибок
        </p>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Kpi
          tone="red"
          icon={<AlertTriangle className="h-5 w-5" />}
          label="Активных инцидентов"
          value={active.length}
          caption={`${critical} критичных`}
        />
        <Kpi
          tone="amber"
          icon={<Gauge className="h-5 w-5" />}
          label="SLO: page-уровень"
          value={pageAlerts}
          caption="сервисов сжигает error budget"
        />
        <Kpi
          tone="emerald"
          icon={<Activity className="h-5 w-5" />}
          label="Здоровых сервисов"
          value={healthyServices}
          caption="alert_level = none"
        />
        <Kpi
          tone="blue"
          icon={<TrendingUp className="h-5 w-5" />}
          label="Уникальных шаблонов"
          value={templates.data?.unique_templates ?? "—"}
          caption={`из ${templates.data?.total_logs ?? 0} логов`}
        />
      </div>

      <div className="mt-8 grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <div className="mb-4 flex items-center justify-between">
            <div>
              <h2 className="text-sm font-semibold text-slate-900">
                Топ инцидентов по impact
              </h2>
              <p className="text-xs text-slate-500">
                Активные инциденты, отсортированные по влиянию
              </p>
            </div>
            <button
              onClick={() => dispatch(setView("incidents"))}
              className="inline-flex items-center gap-1 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50"
            >
              Все инциденты
              <ArrowUpRight className="h-3 w-3" />
            </button>
          </div>
          {incidents.isLoading ? (
            <div className="py-12 text-center text-sm text-slate-400">
              загрузка…
            </div>
          ) : topIncidents.length === 0 ? (
            <div className="rounded-lg border border-dashed border-slate-200 py-10 text-center text-sm text-slate-400">
              Активных инцидентов нет
            </div>
          ) : (
            <div className="space-y-2">
              {topIncidents.map((inc) => (
                <button
                  key={inc.incident_id}
                  onClick={() => {
                    dispatch(setView("incidents"));
                    dispatch(selectIncident(inc.incident_id));
                  }}
                  className="flex w-full items-center gap-4 rounded-xl border border-slate-100 bg-white px-4 py-3 text-left transition hover:border-slate-300 hover:bg-slate-50"
                >
                  <span
                    className={cn(
                      "shrink-0 rounded-md px-2 py-0.5 text-[11px] font-semibold uppercase",
                      severityColors[inc.severity]
                    )}
                  >
                    {inc.severity}
                  </span>
                  <div className="min-w-0 flex-1">
                    <div className="truncate text-sm font-medium text-slate-900">
                      {truncate(inc.title, 70)}
                    </div>
                    <div className="mt-0.5 truncate text-xs text-slate-500">
                      {inc.service} · {inc.environment} · root_cause:{" "}
                      <span className="font-medium text-slate-700">
                        {inc.root_cause_service || "?"}
                      </span>
                    </div>
                  </div>
                  <div className="shrink-0 text-right">
                    <div className="text-sm font-semibold text-slate-900">
                      {formatNumber(inc.impact_score, 2)}
                    </div>
                    <div className="text-[11px] text-slate-500">impact</div>
                  </div>
                  <span
                    className={cn(
                      "shrink-0 rounded-md px-2 py-0.5 text-[11px] font-medium",
                      statusColors[inc.status]
                    )}
                  >
                    {statusLabel[inc.status]}
                  </span>
                </button>
              ))}
            </div>
          )}
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <div className="mb-4">
            <h2 className="text-sm font-semibold text-slate-900">
              SLO по сервисам
            </h2>
            <p className="text-xs text-slate-500">Burn rate за 4 часа</p>
          </div>
          {slo.isLoading ? (
            <div className="py-10 text-center text-sm text-slate-400">
              загрузка…
            </div>
          ) : (
            <ul className="space-y-2">
              {(slo.data?.services ?? []).map((s) => (
                <li
                  key={s.service}
                  className="flex items-center justify-between rounded-lg border border-slate-100 px-3 py-2"
                >
                  <div>
                    <div className="text-sm font-medium text-slate-900">
                      {s.service}
                    </div>
                    <div className="text-[11px] text-slate-500">
                      burn 1h:{" "}
                      {formatNumber(s.windows.find((w) => w.label === "1h")?.burn_rate ?? 0, 1)}
                      ×
                    </div>
                  </div>
                  <span
                    className={cn(
                      "rounded-md px-2 py-0.5 text-[10px] font-semibold",
                      alertLevelColors[s.alert_level]
                    )}
                  >
                    {alertLevelLabel[s.alert_level]}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>

      <div className="mt-6 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <div className="mb-4 flex items-center gap-2">
          <FileText className="h-4 w-4 text-slate-600" />
          <h2 className="text-sm font-semibold text-slate-900">
            Топ шаблонов сообщений (Drain)
          </h2>
        </div>
        {templates.isLoading ? (
          <div className="py-8 text-center text-sm text-slate-400">
            загрузка…
          </div>
        ) : (templates.data?.templates ?? []).length === 0 ? (
          <div className="py-8 text-center text-sm text-slate-400">
            Нет данных
          </div>
        ) : (
          <div className="space-y-1.5">
            {templates.data!.templates.map((t, i) => {
              const total = templates.data!.total_logs || 1;
              const pct = Math.round((t.count / total) * 100);
              return (
                <div key={i} className="relative">
                  <div className="relative h-9 overflow-hidden rounded-lg border border-slate-100 bg-slate-50">
                    <div
                      className="absolute inset-y-0 left-0 bg-gradient-to-r from-blue-100 to-purple-100"
                      style={{ width: `${pct}%` }}
                    />
                    <div className="relative flex h-full items-center justify-between px-3">
                      <code className="truncate font-mono text-xs text-slate-800">
                        {t.template}
                      </code>
                      <div className="ml-3 shrink-0 text-xs font-semibold text-slate-700">
                        {t.count}
                        <span className="ml-1 text-slate-400">({pct}%)</span>
                      </div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
        <div className="mt-2 text-right text-[11px] text-slate-400">
          Последнее обновление: {formatRelativeTime(new Date().toISOString())}
        </div>
      </div>
    </div>
  );
};
