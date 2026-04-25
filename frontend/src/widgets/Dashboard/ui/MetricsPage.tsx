import { BarChart3, Trophy, Target, CircleCheck, CircleX } from "lucide-react";
import { useGetDetectorMetricsQuery } from "@/api";
import type { DetectorReport } from "@/api/rcaApi";
import { cn } from "@/lib/utils";

export const MetricsPage = () => {
  const { data, isLoading, error } = useGetDetectorMetricsQuery();

  if (isLoading) {
    return (
      <div className="mx-auto max-w-7xl px-6 py-12 text-center text-zinc-600">
        загрузка метрик…
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="mx-auto max-w-7xl px-6 py-12">
        <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-6 text-amber-300">
          <h2 className="font-semibold">Отчёт не найден</h2>
          <p className="mt-2 text-sm">
            Сгенерируй labeled dataset и прогоняй оффлайн оценку:
          </p>
          <pre className="mt-3 rounded border border-amber-500/20 bg-amber-950/40 p-3 font-mono text-xs text-amber-200">
            python3 e2e-artifacts/seed_logs.py{"\n"}
            cd backend && docker compose exec api python /app/e2e-artifacts/evaluate_detectors.py
          </pre>
        </div>
      </div>
    );
  }

  const sortedByPrAuc = [...data.results].sort((a, b) => b.pr_auc - a.pr_auc);
  const winner = sortedByPrAuc[0];

  return (
    <div className="mx-auto max-w-7xl px-6 py-8">
      <div className="mb-6 flex items-start justify-between">
        <div>
          <h1 className="flex items-center gap-3 text-2xl font-bold text-zinc-50">
            <span className="inline-block h-5 w-1 rounded-sm bg-violet-500" />
            Сравнение детекторов аномалий
          </h1>
          <p className="mt-1 text-sm text-zinc-500">
            Оценка на labeled synthetic dataset:{" "}
            <b className="text-zinc-300">{data.dataset.points}</b> точек (service × minute),{" "}
            <b className="text-emerald-400">{data.dataset.positives}</b> positive ·{" "}
            <b className="text-zinc-400">{data.dataset.negatives}</b> negative
          </p>
        </div>
        <div className="rounded-lg border border-amber-500/30 bg-gradient-to-br from-amber-500/10 to-amber-500/5 px-4 py-2.5 text-xs">
          <div className="flex items-center gap-1.5 text-amber-400">
            <Trophy className="h-3.5 w-3.5" />
            <span className="font-semibold uppercase tracking-wider">
              Лидер по PR-AUC
            </span>
          </div>
          <div className="mt-0.5 font-mono text-sm font-bold text-zinc-100">
            {winner.name}{" "}
            <span className="text-amber-300">
              = {winner.pr_auc.toFixed(4)}
            </span>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {data.results.map((r) => (
          <DetectorCard
            key={r.name}
            report={r}
            isWinner={r.name === winner.name}
          />
        ))}
      </div>

      <div className="mt-8 rounded-xl border border-zinc-800/60 bg-zinc-900/40 p-6 backdrop-blur">
        <div className="mb-4 flex items-center gap-2">
          <div className="flex h-6 w-6 items-center justify-center rounded-md bg-violet-500/10 ring-1 ring-violet-500/30">
            <BarChart3 className="h-3.5 w-3.5 text-violet-400" />
          </div>
          <h2 className="text-sm font-semibold text-zinc-100">
            Сводная таблица
          </h2>
        </div>
        <div className="overflow-hidden rounded-lg border border-zinc-800/60">
          <table className="w-full">
            <thead className="bg-zinc-950/60 text-[10px] font-semibold uppercase tracking-wider text-zinc-500">
              <tr>
                <th className="px-4 py-2.5 text-left">Метод</th>
                <th className="px-4 py-2.5 text-right">ROC-AUC</th>
                <th className="px-4 py-2.5 text-right">PR-AUC</th>
                <th className="px-4 py-2.5 text-right">F1 (best)</th>
                <th className="px-4 py-2.5 text-right">Precision</th>
                <th className="px-4 py-2.5 text-right">Recall</th>
                <th className="px-4 py-2.5 text-right">Порог</th>
                <th className="px-4 py-2.5 text-right">F1 @3.5</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-800/60 text-sm">
              {data.results.map((r) => (
                <tr
                  key={r.name}
                  className={cn(
                    "transition hover:bg-zinc-900/60",
                    r.name === winner.name && "bg-amber-500/5"
                  )}
                >
                  <td className="px-4 py-2.5 font-medium text-zinc-200">
                    {r.name === winner.name && "🏆 "}
                    {r.name}
                  </td>
                  <td className="px-4 py-2.5 text-right font-mono tabular-nums text-zinc-400">
                    {r.roc_auc.toFixed(4)}
                  </td>
                  <td
                    className={cn(
                      "px-4 py-2.5 text-right font-mono tabular-nums",
                      r.name === winner.name
                        ? "font-bold text-amber-300"
                        : "text-zinc-400"
                    )}
                  >
                    {r.pr_auc.toFixed(4)}
                  </td>
                  <td className="px-4 py-2.5 text-right font-mono tabular-nums text-zinc-400">
                    {r.best.f1.toFixed(4)}
                  </td>
                  <td className="px-4 py-2.5 text-right font-mono tabular-nums text-zinc-400">
                    {r.best.precision.toFixed(2)}
                  </td>
                  <td className="px-4 py-2.5 text-right font-mono tabular-nums text-zinc-400">
                    {r.best.recall.toFixed(2)}
                  </td>
                  <td className="px-4 py-2.5 text-right font-mono tabular-nums text-zinc-500">
                    {r.best.threshold.toFixed(2)}
                  </td>
                  <td className="px-4 py-2.5 text-right font-mono tabular-nums text-zinc-400">
                    {r["at_threshold_3.5"].f1.toFixed(4)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="mt-6 rounded-xl border border-zinc-800/60 bg-zinc-900/40 p-6 backdrop-blur">
        <h2 className="mb-3 text-sm font-semibold text-zinc-100">
          Интерпретация
        </h2>
        <ul className="space-y-2 text-sm text-zinc-300">
          <li>
            <b className="text-zinc-100">ROC-AUC ~ 0.99 у всех</b> — на резком
            burst'е все методы ранжируют аномалии первыми, это не
            различительная метрика.
          </li>
          <li>
            <b className="text-zinc-100">PR-AUC</b> показывает реальную разницу
            при несбалансированных классах (
            <span className="text-emerald-400">{data.dataset.positives}</span>{" "}
            positives vs{" "}
            <span className="text-zinc-400">{data.dataset.negatives}</span>{" "}
            negatives).{" "}
            <b className="text-violet-300">MAD z-score</b> лидирует.
          </li>
          <li>
            <b className="text-zinc-100">Classic z-score</b> деградирует на
            baseline-шуме: редкие transient-ошибки раздувают σ, и score
            настоящего burst'а снижается.
          </li>
          <li>
            <b className="text-zinc-100">Rolling stddev (15m)</b> — короткое
            окно не защищает от выбросов.
          </li>
          <li>
            <b className="text-zinc-100">Isolation Forest</b> — сопоставимая
            ранжирующая способность (PR-AUC 0.84), но scores в другом
            диапазоне, единый порог 3.5 неприменим без калибровки.
          </li>
          <li>
            <b className="text-zinc-100">MAD z-score</b> устойчив к выбросам
            (медианные оценки), даёт{" "}
            <b className="text-emerald-400">Precision = 1.0</b> на оптимальном
            пороге — это эмпирически подтверждает выбор именно MAD в
            production-цикле{" "}
            <code className="rounded border border-zinc-700 bg-zinc-800 px-1.5 py-0.5 font-mono text-xs text-violet-300">
              signals/engine.py
            </code>
            .
          </li>
        </ul>
      </div>
    </div>
  );
};

function DetectorCard({
  report,
  isWinner,
}: {
  report: DetectorReport;
  isWinner: boolean;
}) {
  const prBar = Math.round(report.pr_auc * 100);
  const rocBar = Math.round(report.roc_auc * 100);
  const f1Bar = Math.round(report.best.f1 * 100);

  return (
    <div
      className={cn(
        "rounded-xl border p-5 backdrop-blur",
        isWinner
          ? "border-amber-500/40 bg-gradient-to-br from-amber-500/5 to-zinc-900/60 ring-1 ring-amber-500/20"
          : "border-zinc-800/60 bg-zinc-900/40"
      )}
    >
      <div className="mb-4 flex items-start justify-between">
        <div>
          <div className="flex items-center gap-2">
            {isWinner && (
              <Trophy className="h-4 w-4 text-amber-400 drop-shadow-[0_0_6px_rgba(245,158,11,0.5)]" />
            )}
            <h3 className="font-semibold text-zinc-100">{report.name}</h3>
          </div>
          <div className="mt-1 font-mono text-xs text-zinc-500">
            оптимальный порог:{" "}
            <span className="text-zinc-300">{report.best.threshold.toFixed(2)}</span>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1 font-mono text-xs">
            <CircleCheck className="h-3 w-3 text-emerald-400" />
            <span className="tabular-nums text-zinc-300">
              TP={report.best.tp}
            </span>
          </div>
          <div className="flex items-center gap-1 font-mono text-xs">
            <CircleX className="h-3 w-3 text-rose-400" />
            <span className="tabular-nums text-zinc-300">
              FP={report.best.fp}
            </span>
          </div>
        </div>
      </div>

      <div className="space-y-3">
        <Bar
          label="PR-AUC"
          pct={prBar}
          value={report.pr_auc.toFixed(4)}
          highlight={isWinner}
        />
        <Bar label="ROC-AUC" pct={rocBar} value={report.roc_auc.toFixed(4)} />
        <Bar
          label="F1 (best)"
          pct={f1Bar}
          value={report.best.f1.toFixed(4)}
        />
      </div>

      <div className="mt-4 grid grid-cols-2 gap-2 text-xs">
        <div className="rounded-lg border border-zinc-800 bg-zinc-950/60 px-3 py-2">
          <div className="text-[10px] font-semibold uppercase tracking-wider text-zinc-500">
            Precision
          </div>
          <div className="font-mono text-base font-bold tabular-nums text-zinc-100">
            {report.best.precision.toFixed(2)}
          </div>
        </div>
        <div className="rounded-lg border border-zinc-800 bg-zinc-950/60 px-3 py-2">
          <div className="text-[10px] font-semibold uppercase tracking-wider text-zinc-500">
            Recall
          </div>
          <div className="font-mono text-base font-bold tabular-nums text-zinc-100">
            {report.best.recall.toFixed(2)}
          </div>
        </div>
      </div>

      <div className="mt-3 flex items-center justify-between rounded-lg border border-zinc-800 bg-zinc-950/60 px-3 py-2 text-xs">
        <div className="flex items-center gap-1.5">
          <Target className="h-3 w-3 text-zinc-500" />
          <span className="text-zinc-500">На production-пороге 3.5:</span>
        </div>
        <span
          className={cn(
            "font-mono tabular-nums",
            report["at_threshold_3.5"].f1 >= 0.5
              ? "text-emerald-400"
              : report["at_threshold_3.5"].f1 >= 0.3
              ? "text-amber-400"
              : "text-rose-400"
          )}
        >
          F1 = {report["at_threshold_3.5"].f1.toFixed(4)}
        </span>
      </div>
    </div>
  );
}

function Bar({
  label,
  pct,
  value,
  highlight = false,
}: {
  label: string;
  pct: number;
  value: string;
  highlight?: boolean;
}) {
  return (
    <div>
      <div className="mb-0.5 flex items-center justify-between text-xs">
        <span className="font-mono text-zinc-400">{label}</span>
        <span
          className={cn(
            "font-mono tabular-nums",
            highlight ? "font-bold text-amber-300" : "text-zinc-200"
          )}
        >
          {value}
        </span>
      </div>
      <div className="h-1.5 overflow-hidden rounded-full bg-zinc-800">
        <div
          className={cn(
            "h-full",
            highlight
              ? "bg-gradient-to-r from-amber-500 to-amber-300"
              : "bg-gradient-to-r from-indigo-500 to-violet-500"
          )}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}
