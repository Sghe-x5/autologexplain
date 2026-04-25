/**
 * IncidentDetails — главный экран карточки одного инцидента.
 *
 * Layout:
 *   Row 1: кнопка «Назад»
 *   Row 2: <IncidentHeader> (severity/status/title/переходы FSM)
 *          <IncidentMetaStats> (opened/impact/burn/root_cause)
 *   Row 3 (3 колонки):
 *     col 1-2:
 *       - On-demand RCA (запуск POST /rca/analyze + отображение результата)
 *       - RCA score breakdown (online RCA из incident.context)
 *     col 3:
 *       - <ForecastPanel> (ML-прогноз + SHAP)
 *       - Timeline событий инцидента
 *       - <LifecycleChecklist>
 *   Row 4 (2 колонки):
 *     - <SimilarIncidentsBlock>
 *     - <PostmortemBlock>
 */

import { useState } from "react";
import {
  ArrowLeft,
  Clock,
  Network,
  Target,
  TrendingUp,
  FileSearch,
  ChevronRight,
} from "lucide-react";
import {
  useGetIncidentQuery,
  useGetIncidentTimelineQuery,
  useAnalyzeIncidentMutation,
} from "@/api";
import { AlertLevelBadge } from "@/components/ui/badges";
import { formatDateTime, formatNumber } from "@/widgets/Dashboard/lib/format";
import { cn } from "@/lib/utils";
import { ForecastPanel } from "./ForecastPanel";
import { SimilarIncidentsBlock } from "./SimilarIncidentsBlock";
import { PostmortemBlock } from "./PostmortemBlock";
import { IncidentHeader } from "./incident/IncidentHeader";
import { IncidentMetaStats } from "./incident/IncidentMetaStats";
import { LifecycleChecklist } from "./incident/LifecycleChecklist";

export const IncidentDetails = ({
  incidentId,
  onBack,
}: {
  incidentId: string;
  onBack: () => void;
}) => {
  const { data: incident, isLoading } = useGetIncidentQuery(incidentId);
  const { data: timeline } = useGetIncidentTimelineQuery({ id: incidentId });
  const [analyze, analyzeResult] = useAnalyzeIncidentMutation();
  const [hours, setHours] = useState(4);

  if (isLoading || !incident) {
    return (
      <div className="mx-auto max-w-7xl px-6 py-12 text-center text-zinc-600">
        загрузка…
      </div>
    );
  }

  const rcaBreakdown = extractRcaBreakdown(incident);
  const report = analyzeResult.data;

  return (
    <div className="mx-auto max-w-7xl px-6 py-8">
      <button
        onClick={onBack}
        className="mb-4 inline-flex items-center gap-1.5 rounded-lg px-2 py-1 text-sm text-zinc-400 transition hover:bg-zinc-900 hover:text-zinc-200"
      >
        <ArrowLeft className="h-4 w-4" />
        Вернуться к списку
      </button>

      <IncidentHeader incident={incident} />

      <div className="mb-6">
        <IncidentMetaStats incident={incident} />
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <section className="lg:col-span-2 space-y-6">
          {/* On-demand RCA */}
          <div className="rounded-xl border border-zinc-800/60 bg-zinc-900/40 p-5 backdrop-blur">
            <div className="mb-4 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="flex h-6 w-6 items-center justify-center rounded-md bg-violet-500/10 ring-1 ring-violet-500/30">
                  <Target className="h-3.5 w-3.5 text-violet-400" />
                </div>
                <h2 className="text-sm font-semibold text-zinc-100">
                  On-demand RCA
                </h2>
              </div>
              <div className="flex items-center gap-2">
                <select
                  value={hours}
                  onChange={(e) => setHours(Number(e.target.value))}
                  className="rounded-md border border-zinc-700 bg-zinc-800/80 px-2 py-1 font-mono text-xs text-zinc-200 outline-none focus:border-violet-500/50"
                  data-test-id="rca-hours-select"
                >
                  <option value={1}>1 час</option>
                  <option value={4}>4 часа</option>
                  <option value={12}>12 часов</option>
                  <option value={24}>24 часа</option>
                </select>
                <button
                  onClick={() =>
                    analyze({
                      fingerprint: incident.fingerprint,
                      hours,
                      use_llm: false,
                    })
                  }
                  disabled={analyzeResult.isLoading}
                  className="inline-flex items-center gap-1.5 rounded-lg bg-gradient-to-r from-indigo-500 to-violet-600 px-3 py-1.5 text-xs font-semibold text-white shadow-lg shadow-indigo-500/20 transition hover:from-indigo-400 hover:to-violet-500 disabled:opacity-50"
                  data-test-id="rca-analyze-button"
                >
                  <TrendingUp className="h-3 w-3" />
                  {analyzeResult.isLoading ? "Анализ…" : "Запустить RCA"}
                </button>
              </div>
            </div>

            {!report && !analyzeResult.isLoading && (
              <div className="rounded-lg border border-dashed border-zinc-800 bg-zinc-950/40 p-8 text-center">
                <FileSearch className="mx-auto h-8 w-8 text-zinc-700" />
                <p className="mt-2 text-sm text-zinc-500">
                  Нажми «Запустить RCA», чтобы собрать полный отчёт: cascade
                  path, timeline аномалий, evidence-шаблоны и уровень confidence.
                </p>
              </div>
            )}

            {analyzeResult.isLoading && (
              <div className="py-12 text-center font-mono text-xs text-zinc-500">
                <span className="text-violet-400">&gt;</span> Читаем логи →{" "}
                <span className="text-rose-400">MAD z-score</span> → граф
                зависимостей → <span className="text-amber-400">Drain</span>{" "}
                → SLO…
              </div>
            )}

            {analyzeResult.error && (
              <div className="rounded-lg border border-rose-500/30 bg-rose-500/10 p-4 text-sm text-rose-300">
                Ошибка анализа. Попробуй увеличить окно или проверь backend.
              </div>
            )}

            {report && (
              <div className="space-y-5">
                {/* Sticky bar */}
                <div className="grid grid-cols-2 gap-4 rounded-lg border border-zinc-800 bg-zinc-950/60 p-4 sm:grid-cols-4">
                  <div>
                    <div className="text-[10px] font-semibold uppercase tracking-wider text-zinc-500">
                      Root cause
                    </div>
                    <div className="mt-1 text-lg font-bold text-zinc-50">
                      {report.root_cause_service}
                    </div>
                    <div className="text-[11px] text-zinc-500">
                      · {report.root_cause_category}
                    </div>
                  </div>
                  <div>
                    <div className="text-[10px] font-semibold uppercase tracking-wider text-zinc-500">
                      Confidence
                    </div>
                    <div
                      className={cn(
                        "mt-1 text-2xl font-bold tabular-nums",
                        report.confidence >= 0.75
                          ? "text-emerald-400"
                          : report.confidence >= 0.5
                          ? "text-amber-400"
                          : "text-rose-400"
                      )}
                    >
                      {Math.round(report.confidence * 100)}%
                    </div>
                  </div>
                  <div>
                    <div className="text-[10px] font-semibold uppercase tracking-wider text-zinc-500">
                      Max z-score
                    </div>
                    <div className="mt-1 text-2xl font-bold tabular-nums text-rose-400">
                      {formatNumber(report.anomaly_score, 2)}
                    </div>
                  </div>
                  <div>
                    <div className="text-[10px] font-semibold uppercase tracking-wider text-zinc-500">
                      Alert
                    </div>
                    <div className="mt-1">
                      <AlertLevelBadge value={report.alert_level} />
                    </div>
                  </div>
                </div>

                {report.cascade_path.length > 0 && (
                  <div>
                    <div className="mb-2 flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-wider text-zinc-500">
                      <Network className="h-3 w-3" />
                      Cascade path
                    </div>
                    <div className="flex flex-wrap items-center gap-2">
                      {report.cascade_path.map((svc, i) => (
                        <span key={svc} className="flex items-center gap-2">
                          <span className="inline-flex items-center gap-1.5 rounded-lg border border-violet-500/30 bg-violet-500/10 px-3 py-1 font-mono text-xs font-medium text-violet-300">
                            <span className="h-1.5 w-1.5 rounded-full bg-violet-400 shadow-[0_0_6px_1px_rgba(168,85,247,0.6)]" />
                            {svc}
                          </span>
                          {i < report.cascade_path.length - 1 && (
                            <ChevronRight className="h-3.5 w-3.5 text-zinc-600" />
                          )}
                        </span>
                      ))}
                    </div>
                    {report.affected_services.length > 0 && (
                      <div className="mt-2 flex flex-wrap items-center gap-1 text-[11px] text-zinc-500">
                        <span>Затронуто:</span>
                        {report.affected_services.map((s) => (
                          <code
                            key={s}
                            className="rounded border border-zinc-800 bg-zinc-900 px-1.5 py-0.5 font-mono text-zinc-300"
                          >
                            {s}
                          </code>
                        ))}
                      </div>
                    )}
                  </div>
                )}

                {report.summary && (
                  <div className="rounded-lg border border-zinc-800 bg-zinc-950/60 p-4">
                    <div className="mb-1 text-[10px] font-semibold uppercase tracking-wider text-zinc-500">
                      Summary
                    </div>
                    <p className="text-sm leading-relaxed text-zinc-300">
                      {report.summary}
                    </p>
                  </div>
                )}

                {report.evidence_templates.length > 0 && (
                  <div>
                    <div className="mb-2 text-[10px] font-semibold uppercase tracking-wider text-zinc-500">
                      Evidence templates (Drain)
                    </div>
                    <div className="overflow-hidden rounded-lg border border-zinc-800 bg-zinc-950/80 font-mono text-xs">
                      <div className="border-b border-zinc-800 px-3 py-1.5 text-[10px] text-zinc-600">
                        # {report.evidence_templates.length} evidence · spike-ratio ranking
                      </div>
                      {report.evidence_templates.map((t, i) => (
                        <div
                          key={i}
                          className="flex items-start gap-2 px-3 py-2 text-zinc-200 [&:not(:last-child)]:border-b [&:not(:last-child)]:border-zinc-800/40"
                        >
                          <span className="shrink-0 text-violet-500">&gt;</span>
                          <code className="block whitespace-pre-wrap break-all">
                            {t
                              .split("<*>")
                              .flatMap((part, idx, arr) => {
                                const nodes: React.ReactNode[] = [
                                  <span key={`p${idx}`}>{part}</span>,
                                ];
                                if (idx < arr.length - 1) {
                                  nodes.push(
                                    <span
                                      key={`w${idx}`}
                                      className="text-amber-400"
                                    >
                                      {"<*>"}
                                    </span>
                                  );
                                }
                                return nodes;
                              })}
                          </code>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {report.timeline.length > 0 && (
                  <div>
                    <div className="mb-2 text-[10px] font-semibold uppercase tracking-wider text-zinc-500">
                      Anomaly timeline
                    </div>
                    <div className="max-h-64 space-y-1 overflow-y-auto rounded-lg border border-zinc-800 bg-zinc-950/60 p-2">
                      {report.timeline.map((ev, i) => {
                        const z = ev.z_score;
                        const zColor =
                          z >= 5 ? "text-rose-400" : z >= 4 ? "text-amber-400" : "text-zinc-400";
                        return (
                          <div
                            key={i}
                            className="flex items-center gap-2 rounded px-2.5 py-1.5 font-mono text-xs hover:bg-zinc-900/60"
                          >
                            <TrendingUp
                              className={cn("h-3 w-3 shrink-0", zColor)}
                            />
                            <span className="shrink-0 text-zinc-500">
                              {ev.time}
                            </span>
                            <span className="shrink-0 font-medium text-zinc-200">
                              {ev.service}
                            </span>
                            <span className="shrink-0 text-zinc-500">
                              ×{ev.count}
                            </span>
                            <span
                              className={cn(
                                "ml-auto shrink-0 tabular-nums",
                                zColor
                              )}
                            >
                              z={formatNumber(ev.z_score, 2)}
                            </span>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>

          {Object.keys(rcaBreakdown).length > 0 && (
            <div className="rounded-xl border border-zinc-800/60 bg-zinc-900/40 p-5 backdrop-blur">
              <div className="mb-4 flex items-center gap-2">
                <div className="flex h-6 w-6 items-center justify-center rounded-md bg-violet-500/10 ring-1 ring-violet-500/30">
                  <Target className="h-3.5 w-3.5 text-violet-400" />
                </div>
                <h2 className="text-sm font-semibold text-zinc-100">
                  RCA score breakdown (online)
                </h2>
                <span className="ml-auto font-mono text-xs text-zinc-500">
                  total:{" "}
                  <span className="font-semibold text-violet-300">
                    {formatNumber(incident.root_cause_score, 2)}
                  </span>
                </span>
              </div>
              <div className="space-y-2.5">
                {RCA_FACTORS.map(({ key, weight }) => {
                  const v = Number(rcaBreakdown[key] ?? 0);
                  return (
                    <div key={key}>
                      <div className="mb-0.5 flex items-center justify-between text-xs">
                        <span className="font-mono text-zinc-300">
                          {key}
                          <span className="ml-1 text-zinc-600">×{weight}</span>
                        </span>
                        <span className="font-mono tabular-nums text-zinc-200">
                          {formatNumber(v, 3)}
                        </span>
                      </div>
                      <div className="h-1.5 overflow-hidden rounded-full bg-zinc-800">
                        <div
                          className="h-full bg-gradient-to-r from-indigo-500 to-violet-500"
                          style={{ width: `${Math.min(100, v * 100)}%` }}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </section>

        <section className="space-y-6">
          <ForecastPanel
            service={incident.service}
            environment={incident.environment}
          />

          <div className="rounded-xl border border-zinc-800/60 bg-zinc-900/40 p-5 backdrop-blur">
            <div className="mb-4 flex items-center gap-2">
              <div className="flex h-6 w-6 items-center justify-center rounded-md bg-sky-500/10 ring-1 ring-sky-500/30">
                <Clock className="h-3.5 w-3.5 text-sky-400" />
              </div>
              <h2 className="text-sm font-semibold text-zinc-100">Timeline</h2>
            </div>
            {!timeline || timeline.events.length === 0 ? (
              <div className="py-8 text-center text-sm text-zinc-600">
                Нет событий
              </div>
            ) : (
              <ol className="relative ml-3 border-l border-zinc-800">
                {timeline.events.map((ev) => (
                  <li key={ev.event_id} className="mb-4 ml-4">
                    <div className="absolute -left-[5px] mt-1 h-2.5 w-2.5 rounded-full border-2 border-zinc-950 bg-sky-400 shadow-[0_0_6px_1px_rgba(56,189,248,0.5)]" />
                    <div className="font-mono text-[11px] text-zinc-500">
                      {formatDateTime(ev.event_time)}
                    </div>
                    <div className="text-sm font-medium text-zinc-100">
                      {eventLabel(ev.event_type)}
                    </div>
                    <div className="font-mono text-[11px] text-zinc-600">
                      actor: {ev.actor}
                    </div>
                  </li>
                ))}
              </ol>
            )}
          </div>

          <LifecycleChecklist incident={incident} />
        </section>
      </div>

      <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-2">
        <SimilarIncidentsBlock incidentId={incidentId} />
        <PostmortemBlock incidentId={incidentId} />
      </div>
    </div>
  );
};

// ─── helpers ──────────────────────────────────────────────────────────────

const RCA_FACTORS: { key: string; weight: number }[] = [
  { key: "anomaly", weight: 0.35 },
  { key: "earliness", weight: 0.25 },
  { key: "fanout", weight: 0.2 },
  { key: "criticality", weight: 0.2 },
];

function extractRcaBreakdown(incident: {
  context?: Record<string, unknown>;
  context_json?: string;
}): Record<string, number> {
  const fromContext = incident.context?.rca_breakdown as
    | Record<string, number>
    | undefined;
  if (fromContext) return fromContext;
  try {
    const parsed = JSON.parse(incident.context_json || "{}");
    return parsed.rca_breakdown ?? {};
  } catch {
    return {};
  }
}

function eventLabel(t: string): string {
  const map: Record<string, string> = {
    opened: "Инцидент открыт",
    candidate_attached: "Прикреплён кандидат",
    reopened: "Переоткрыт",
    rca_recomputed: "RCA пересчитан",
    status_changed: "Изменение статуса",
  };
  return map[t] ?? t;
}
