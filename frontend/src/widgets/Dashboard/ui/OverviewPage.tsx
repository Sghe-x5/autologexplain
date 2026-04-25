import { useMemo } from "react";
import { useDispatch } from "react-redux";
import {
  AlertTriangle,
  Activity,
  Gauge,
  TrendingUp,
  FileText,
  ChevronDown,
  ChevronRight,
  Code2,
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
  severityColors,
  statusLabel,
  statusColors,
  truncate,
} from "@/widgets/Dashboard/lib/format";
import { cn } from "@/lib/utils";

type Tone = "red" | "amber" | "emerald" | "violet";

const toneAccent: Record<Tone, { stroke: string; fill: string; text: string; iconBg: string; border: string }> = {
  red:     { stroke: "#f43f5e", fill: "rgba(244,63,94,0.15)",   text: "text-rose-400",    iconBg: "bg-rose-500/10 text-rose-400 ring-1 ring-rose-500/30",       border: "border-rose-500/20" },
  amber:   { stroke: "#f59e0b", fill: "rgba(245,158,11,0.15)",  text: "text-amber-400",   iconBg: "bg-amber-500/10 text-amber-400 ring-1 ring-amber-500/30",    border: "border-amber-500/20" },
  emerald: { stroke: "#10b981", fill: "rgba(16,185,129,0.15)",  text: "text-emerald-400", iconBg: "bg-emerald-500/10 text-emerald-400 ring-1 ring-emerald-500/30", border: "border-emerald-500/20" },
  violet:  { stroke: "#a855f7", fill: "rgba(168,85,247,0.15)",  text: "text-violet-400",  iconBg: "bg-violet-500/10 text-violet-400 ring-1 ring-violet-500/30",  border: "border-violet-500/20" },
};

// Deterministic pseudo-sparkline from a seed — same inputs produce same path
function seededPoints(seed: number, count = 12, trend: "up" | "down" | "flat" = "up"): number[] {
  const pts: number[] = [];
  let v = 0.3 + ((seed * 137) % 50) / 200;
  for (let i = 0; i < count; i++) {
    const noise = ((seed * (i + 1) * 31) % 100) / 500;
    const trendDelta = trend === "up" ? 0.04 : trend === "down" ? -0.04 : 0;
    v += trendDelta + noise - 0.05;
    v = Math.max(0.05, Math.min(0.95, v));
    pts.push(v);
  }
  return pts;
}

function Sparkline({
  points,
  stroke,
  fill,
  width = 220,
  height = 40,
}: {
  points: number[];
  stroke: string;
  fill: string;
  width?: number;
  height?: number;
}) {
  if (points.length < 2) return null;
  const step = width / (points.length - 1);
  const toXY = (v: number, i: number) => [i * step, height - v * height];
  const path = points
    .map((v, i) => {
      const [x, y] = toXY(v, i);
      return `${i === 0 ? "M" : "L"} ${x.toFixed(1)} ${y.toFixed(1)}`;
    })
    .join(" ");
  const areaPath = `${path} L ${width} ${height} L 0 ${height} Z`;
  const last = points[points.length - 1];
  const [lastX, lastY] = toXY(last, points.length - 1);
  return (
    <svg
      viewBox={`0 0 ${width} ${height}`}
      className="h-10 w-full"
      preserveAspectRatio="none"
    >
      <path d={areaPath} fill={fill} />
      <path d={path} stroke={stroke} strokeWidth="1.5" fill="none" strokeLinecap="round" strokeLinejoin="round" />
      <circle cx={lastX} cy={lastY} r="2.5" fill={stroke} />
    </svg>
  );
}

function Kpi({
  icon,
  label,
  value,
  caption,
  tone,
  trend = "up",
  seed,
}: {
  icon: React.ReactNode;
  label: string;
  value: React.ReactNode;
  caption?: React.ReactNode;
  tone: Tone;
  trend?: "up" | "down" | "flat";
  seed: number;
}) {
  const t = toneAccent[tone];
  const points = seededPoints(seed, 14, trend);
  return (
    <div
      className={cn(
        "relative overflow-hidden rounded-xl border bg-zinc-900/60 p-5 backdrop-blur",
        "transition hover:bg-zinc-900/80",
        t.border
      )}
    >
      <div className="flex items-start justify-between">
        <div className="text-[10px] font-semibold uppercase tracking-wider text-zinc-500">
          {label}
        </div>
        <div className={cn("flex h-7 w-7 items-center justify-center rounded-md", t.iconBg)}>
          {icon}
        </div>
      </div>
      <div className="mt-3 text-4xl font-semibold tabular-nums text-zinc-50">{value}</div>
      {caption && <div className="mt-1 text-xs text-zinc-500">{caption}</div>}
      <div className="pointer-events-none mt-3 -mb-2 -mx-1">
        <Sparkline points={points} stroke={t.stroke} fill={t.fill} />
      </div>
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
  const errorCount = active.filter((i) => i.severity === "error").length;
  const warnCount = active.filter((i) => i.severity === "warning").length;
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

  // Accent palette for Drain templates (cycles through tones by index)
  const drainAccents = [
    { bar: "from-rose-500/60 to-rose-500/10",     dot: "bg-rose-400"    },
    { bar: "from-amber-500/60 to-amber-500/10",   dot: "bg-amber-400"   },
    { bar: "from-sky-500/60 to-sky-500/10",       dot: "bg-sky-400"     },
    { bar: "from-violet-500/60 to-violet-500/10", dot: "bg-violet-400"  },
    { bar: "from-emerald-500/60 to-emerald-500/10", dot: "bg-emerald-400" },
  ];

  return (
    <div className="mx-auto max-w-7xl px-6 py-8">
      <div className="mb-8 flex items-end justify-between">
        <div>
          <h1 className="flex items-center gap-3 text-2xl font-bold text-zinc-50">
            <span className="inline-block h-5 w-1 rounded-sm bg-violet-500" />
            Обзор системы
            {incidents.data && (
              <span className="text-xs font-normal text-zinc-500">
                updated just now
              </span>
            )}
          </h1>
          <p className="mt-1 text-sm text-zinc-500">
            Текущее состояние инцидентов, SLO и топ-шаблоны ошибок
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Kpi
          tone="red"
          icon={<AlertTriangle className="h-4 w-4" />}
          label="Активных инцидентов"
          value={active.length}
          caption={
            <>
              <span className="text-rose-400">{critical} critical</span>
              {" · "}
              <span className="text-orange-400">{errorCount} error</span>
              {" · "}
              <span className="text-amber-400">{warnCount} warn</span>
            </>
          }
          trend="up"
          seed={active.length + 1}
        />
        <Kpi
          tone="amber"
          icon={<Gauge className="h-4 w-4" />}
          label="SLO · page-уровень"
          value={pageAlerts}
          caption="сервисов сжигают error budget"
          trend="up"
          seed={pageAlerts + 7}
        />
        <Kpi
          tone="emerald"
          icon={<Activity className="h-4 w-4" />}
          label="Здоровых сервисов"
          value={healthyServices}
          caption="alert_level = none"
          trend="down"
          seed={healthyServices + 3}
        />
        <Kpi
          tone="violet"
          icon={<Code2 className="h-4 w-4" />}
          label="Уникальных шаблонов"
          value={templates.data?.unique_templates ?? "—"}
          caption={`из ${templates.data?.total_logs ?? 0} логов`}
          trend="up"
          seed={(templates.data?.unique_templates ?? 3) + 11}
        />
      </div>

      <div className="mt-8 grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2 rounded-xl border border-zinc-800/60 bg-zinc-900/40 p-5 backdrop-blur">
          <div className="mb-4 flex items-center justify-between">
            <div>
              <h2 className="text-sm font-semibold text-zinc-100">
                Топ инцидентов по impact
              </h2>
              <p className="text-xs text-zinc-500">
                Активные, отсортированы по влиянию
              </p>
            </div>
            <button
              onClick={() => dispatch(setView("incidents"))}
              className="inline-flex items-center gap-1 rounded-md border border-zinc-700 bg-zinc-800/60 px-3 py-1.5 text-xs font-medium text-zinc-300 transition hover:border-violet-500/40 hover:text-violet-300"
            >
              Все инциденты
              <ChevronRight className="h-3 w-3" />
            </button>
          </div>
          {incidents.isLoading ? (
            <div className="py-12 text-center text-sm text-zinc-600">
              загрузка…
            </div>
          ) : topIncidents.length === 0 ? (
            <div className="rounded-lg border border-dashed border-zinc-800 py-10 text-center text-sm text-zinc-600">
              Активных инцидентов нет
            </div>
          ) : (
            <div className="space-y-1.5">
              {topIncidents.map((inc) => (
                <button
                  key={inc.incident_id}
                  onClick={() => {
                    dispatch(setView("incidents"));
                    dispatch(selectIncident(inc.incident_id));
                  }}
                  className="group flex w-full items-center gap-3 rounded-lg border border-transparent bg-zinc-900/40 px-3 py-2.5 text-left transition hover:border-zinc-700 hover:bg-zinc-900"
                >
                  <span className="h-8 w-0.5 shrink-0 rounded-full bg-rose-500/70" />
                  <span
                    className={cn(
                      "shrink-0 rounded px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-wider",
                      severityColors[inc.severity]
                    )}
                  >
                    ● {inc.severity}
                  </span>
                  <div className="min-w-0 flex-1">
                    <div className="truncate text-sm font-medium text-zinc-100">
                      {truncate(inc.title, 60)}
                    </div>
                    <div className="mt-0.5 truncate font-mono text-[10px] text-zinc-500">
                      {inc.service} · {inc.environment} · root:{" "}
                      <span className="font-medium text-violet-400">
                        {inc.root_cause_service || "?"}
                      </span>
                    </div>
                  </div>
                  <div className="shrink-0 text-right">
                    <div className="text-sm font-semibold tabular-nums text-zinc-100">
                      {formatNumber(inc.impact_score, 2)}
                    </div>
                    <div className="text-[10px] uppercase tracking-wider text-zinc-600">impact</div>
                  </div>
                  <span
                    className={cn(
                      "shrink-0 rounded px-2 py-0.5 text-[10px] font-medium",
                      statusColors[inc.status]
                    )}
                  >
                    {statusLabel[inc.status].toLowerCase()}
                  </span>
                </button>
              ))}
            </div>
          )}
        </div>

        <div className="rounded-xl border border-zinc-800/60 bg-zinc-900/40 p-5 backdrop-blur">
          <div className="mb-4">
            <h2 className="text-sm font-semibold text-zinc-100">
              SLO по сервисам
            </h2>
            <p className="text-xs text-zinc-500">Burn rate за 4 часа</p>
          </div>
          {slo.isLoading ? (
            <div className="py-10 text-center text-sm text-zinc-600">
              загрузка…
            </div>
          ) : (
            <ul className="space-y-1.5">
              {(slo.data?.services ?? []).map((s, i) => {
                const burn1h = s.windows.find((w) => w.label === "1h")?.burn_rate ?? 0;
                const tone: Tone = s.alert_level === "none" ? "emerald" : s.alert_level === "warning" ? "amber" : "red";
                const t = toneAccent[tone];
                return (
                  <li
                    key={s.service}
                    className="flex items-center gap-3 rounded-lg border border-zinc-800/60 bg-zinc-900/40 px-3 py-2"
                  >
                    <div className="min-w-0 flex-1">
                      <div className="truncate font-mono text-xs font-medium text-zinc-200">
                        {s.service}
                      </div>
                      <div className="mt-0.5 font-mono text-[10px] text-zinc-500">
                        burn 1h:{" "}
                        <span className={t.text}>
                          {formatNumber(burn1h, 1)}x
                        </span>
                      </div>
                    </div>
                    <div className="w-16 shrink-0">
                      <Sparkline
                        points={seededPoints(i + s.service.length, 10, s.alert_level === "none" ? "down" : "up")}
                        stroke={t.stroke}
                        fill={t.fill}
                        width={64}
                        height={24}
                      />
                    </div>
                    <span
                      className={cn(
                        "shrink-0 rounded px-2 py-0.5 text-[9px] font-bold uppercase tracking-wider",
                        alertLevelColors[s.alert_level]
                      )}
                    >
                      ● {alertLevelLabel[s.alert_level]}
                    </span>
                  </li>
                );
              })}
            </ul>
          )}
        </div>
      </div>

      <div className="mt-6 rounded-xl border border-zinc-800/60 bg-zinc-900/40 p-5 backdrop-blur">
        <div className="mb-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <FileText className="h-4 w-4 text-violet-400" />
            <h2 className="text-sm font-semibold text-zinc-100">
              Топ шаблонов сообщений{" "}
              <span className="font-normal text-zinc-500">(Drain)</span>
            </h2>
          </div>
          <div className="font-mono text-[10px] text-zinc-600">
            {templates.data?.total_logs ?? 0} логов ·{" "}
            {templates.data?.unique_templates ?? 0} уникальных
          </div>
        </div>
        {templates.isLoading ? (
          <div className="py-8 text-center text-sm text-zinc-600">
            загрузка…
          </div>
        ) : (templates.data?.templates ?? []).length === 0 ? (
          <div className="py-8 text-center text-sm text-zinc-600">
            Нет данных
          </div>
        ) : (
          <div className="space-y-1.5">
            {templates.data!.templates.map((t, i) => {
              const total = templates.data!.total_logs || 1;
              const pct = Math.round((t.count / total) * 100);
              const accent = drainAccents[i % drainAccents.length];
              return (
                <div key={i} className="relative">
                  <div className="relative flex h-10 items-center overflow-hidden rounded-lg border border-zinc-800/60 bg-zinc-950/60">
                    <div
                      className={cn(
                        "absolute inset-y-0 left-0 bg-gradient-to-r",
                        accent.bar
                      )}
                      style={{ width: `${pct}%` }}
                    />
                    <div className="relative flex h-full w-full items-center justify-between gap-3 px-3">
                      <div className="flex min-w-0 items-center gap-2">
                        <ChevronDown className="h-3 w-3 shrink-0 text-zinc-600" />
                        <code className="truncate font-mono text-xs text-zinc-200">
                          {t.template}
                        </code>
                      </div>
                      <div className="flex shrink-0 items-center gap-3 font-mono text-xs">
                        <span className="font-semibold text-zinc-100">{t.count}</span>
                        <span className="text-zinc-500">({pct}%)</span>
                      </div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
        <div className="mt-3 flex items-center gap-1.5 text-[10px] text-zinc-600">
          <TrendingUp className="h-3 w-3" />
          <span>Drain streaming clustering · обновляется раз в минуту</span>
        </div>
      </div>
    </div>
  );
};
