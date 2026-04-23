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
} from "lucide-react";
import {
  useGetIncidentQuery,
  useGetIncidentTimelineQuery,
  useAnalyzeIncidentMutation,
} from "@/api";
import { AlertLevelBadge } from "@/components/ui/badges";
import { formatDateTime, formatNumber } from "@/widgets/Dashboard/lib/format";
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
      <div className="mx-auto max-w-7xl px-6 py-12 text-center text-slate-400">
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
        className="mb-4 inline-flex items-center gap-1.5 rounded-lg px-2 py-1 text-sm text-slate-600 hover:bg-slate-100"
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
          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
            <div className="mb-4 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Target className="h-4 w-4 text-slate-600" />
                <h2 className="text-sm font-semibold text-slate-900">
                  On-demand RCA
                </h2>
              </div>
              <div className="flex items-center gap-2">
                <select
                  value={hours}
                  onChange={(e) => setHours(Number(e.target.value))}
                  className="rounded-md border border-slate-200 bg-white px-2 py-1 text-xs"
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
                  className="inline-flex items-center gap-1.5 rounded-lg bg-gradient-to-r from-blue-600 to-purple-600 px-3 py-1.5 text-xs font-semibold text-white shadow-sm transition hover:from-blue-700 hover:to-purple-700 disabled:opacity-50"
                  data-test-id="rca-analyze-button"
                >
                  <TrendingUp className="h-3 w-3" />
                  {analyzeResult.isLoading ? "Анализ…" : "Запустить RCA"}
                </button>
              </div>
            </div>

            {!report && !analyzeResult.isLoading && (
              <div className="rounded-xl border border-dashed border-slate-200 p-8 text-center">
                <FileSearch className="mx-auto h-8 w-8 text-slate-300" />
                <p className="mt-2 text-sm text-slate-500">
                  Нажми «Запустить RCA», чтобы собрать полный отчёт: cascade
                  path, timeline аномалий, evidence-шаблоны и уровень confidence.
                </p>
              </div>
            )}

            {analyzeResult.isLoading && (
              <div className="py-12 text-center text-sm text-slate-400">
                Читаем логи → MAD z-score → граф зависимостей → Drain-кластеры → SLO…
              </div>
            )}

            {analyzeResult.error && (
              <div className="rounded-xl bg-red-50 p-4 text-sm text-red-700">
                Ошибка анализа. Попробуй увеличить окно или проверь backend.
              </div>
            )}

            {report && (
              <div className="space-y-5">
                {/* Sticky bar */}
                <div className="flex flex-wrap items-start gap-3 rounded-xl bg-slate-50 p-4">
                  <div className="flex-1 min-w-[200px]">
                    <div className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">
                      Root cause
                    </div>
                    <div className="mt-1 text-lg font-bold text-slate-900">
                      {report.root_cause_service}{" "}
                      <span className="text-sm font-normal text-slate-500">
                        · {report.root_cause_category}
                      </span>
                    </div>
                  </div>
                  <div>
                    <div className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">
                      Confidence
                    </div>
                    <div className="mt-1 text-lg font-bold text-slate-900">
                      {Math.round(report.confidence * 100)}%
                    </div>
                  </div>
                  <div>
                    <div className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">
                      Max z-score
                    </div>
                    <div className="mt-1 text-lg font-bold text-slate-900">
                      {formatNumber(report.anomaly_score, 2)}
                    </div>
                  </div>
                  <div>
                    <div className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">
                      Alert
                    </div>
                    <div className="mt-1">
                      <AlertLevelBadge value={report.alert_level} />
                    </div>
                  </div>
                </div>

                {report.cascade_path.length > 0 && (
                  <div>
                    <div className="mb-2 flex items-center gap-1.5 text-xs font-semibold text-slate-700">
                      <Network className="h-3 w-3" />
                      Cascade path
                    </div>
                    <div className="flex flex-wrap items-center gap-2">
                      {report.cascade_path.map((svc, i) => (
                        <span key={svc} className="flex items-center gap-2">
                          <span className="rounded-lg border border-blue-200 bg-blue-50 px-3 py-1 text-sm font-medium text-blue-800">
                            {svc}
                          </span>
                          {i < report.cascade_path.length - 1 && (
                            <span className="text-slate-400">→</span>
                          )}
                        </span>
                      ))}
                    </div>
                    {report.affected_services.length > 0 && (
                      <div className="mt-2 text-xs text-slate-500">
                        Затронуто:{" "}
                        {report.affected_services.map((s) => (
                          <span
                            key={s}
                            className="mr-1 inline-block rounded bg-slate-100 px-1.5 py-0.5 font-mono text-[11px] text-slate-700"
                          >
                            {s}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                )}

                {report.summary && (
                  <div className="rounded-xl border border-slate-200 bg-white p-4">
                    <div className="mb-1 text-[10px] font-semibold uppercase tracking-wider text-slate-500">
                      Summary
                    </div>
                    <p className="text-sm leading-relaxed text-slate-700">
                      {report.summary}
                    </p>
                  </div>
                )}

                {report.evidence_templates.length > 0 && (
                  <div>
                    <div className="mb-2 text-xs font-semibold text-slate-700">
                      Evidence templates (Drain)
                    </div>
                    <div className="space-y-1.5">
                      {report.evidence_templates.map((t, i) => (
                        <code
                          key={i}
                          className="block truncate rounded-md bg-slate-900 px-3 py-1.5 font-mono text-[12px] text-slate-100"
                        >
                          {t}
                        </code>
                      ))}
                    </div>
                  </div>
                )}

                {report.timeline.length > 0 && (
                  <div>
                    <div className="mb-2 text-xs font-semibold text-slate-700">
                      Anomaly timeline
                    </div>
                    <div className="max-h-64 space-y-1 overflow-y-auto rounded-lg border border-slate-100 bg-slate-50 p-2">
                      {report.timeline.map((ev, i) => (
                        <div
                          key={i}
                          className="flex items-center gap-2 rounded bg-white px-2.5 py-1.5 text-xs"
                        >
                          <TrendingUp className="h-3 w-3 shrink-0 text-orange-500" />
                          <span className="shrink-0 font-mono text-slate-500">
                            {ev.time}
                          </span>
                          <span className="shrink-0 font-medium text-slate-800">
                            {ev.service}
                          </span>
                          <span className="shrink-0 text-slate-500">
                            ×{ev.count}
                          </span>
                          <span className="ml-auto shrink-0 font-mono text-orange-600">
                            z={formatNumber(ev.z_score, 2)}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>

          {Object.keys(rcaBreakdown).length > 0 && (
            <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
              <div className="mb-4 flex items-center gap-2">
                <Target className="h-4 w-4 text-slate-600" />
                <h2 className="text-sm font-semibold text-slate-900">
                  RCA score breakdown (online)
                </h2>
                <span className="ml-auto font-mono text-xs text-slate-500">
                  total: {formatNumber(incident.root_cause_score, 2)}
                </span>
              </div>
              <div className="space-y-2">
                {RCA_FACTORS.map(({ key, weight }) => {
                  const v = Number(rcaBreakdown[key] ?? 0);
                  return (
                    <div key={key}>
                      <div className="mb-0.5 flex items-center justify-between text-xs">
                        <span className="font-medium text-slate-700">
                          {key}
                          <span className="ml-1 text-slate-400">×{weight}</span>
                        </span>
                        <span className="font-mono text-slate-700">
                          {formatNumber(v, 3)}
                        </span>
                      </div>
                      <div className="h-2 overflow-hidden rounded-full bg-slate-100">
                        <div
                          className="h-full bg-gradient-to-r from-blue-500 to-purple-500"
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

          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
            <div className="mb-4 flex items-center gap-2">
              <Clock className="h-4 w-4 text-slate-600" />
              <h2 className="text-sm font-semibold text-slate-900">Timeline</h2>
            </div>
            {!timeline || timeline.events.length === 0 ? (
              <div className="py-8 text-center text-sm text-slate-400">
                Нет событий
              </div>
            ) : (
              <ol className="relative ml-3 border-l border-slate-200">
                {timeline.events.map((ev) => (
                  <li key={ev.event_id} className="mb-4 ml-4">
                    <div className="absolute -left-[5px] mt-1 h-2.5 w-2.5 rounded-full border border-white bg-blue-500" />
                    <div className="text-[11px] text-slate-400">
                      {formatDateTime(ev.event_time)}
                    </div>
                    <div className="text-sm font-medium text-slate-900">
                      {eventLabel(ev.event_type)}
                    </div>
                    <div className="text-[11px] text-slate-500">
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
