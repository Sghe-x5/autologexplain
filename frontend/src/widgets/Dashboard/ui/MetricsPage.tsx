import { BarChart3, Trophy, Target, CircleCheck, CircleX } from "lucide-react";
import { useGetDetectorMetricsQuery } from "@/api";
import type { DetectorReport } from "@/api/rcaApi";
import { cn } from "@/lib/utils";

export const MetricsPage = () => {
  const { data, isLoading, error } = useGetDetectorMetricsQuery();

  if (isLoading) {
    return (
      <div className="mx-auto max-w-7xl px-6 py-12 text-center text-slate-400">
        загрузка метрик…
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="mx-auto max-w-7xl px-6 py-12">
        <div className="rounded-xl border border-amber-200 bg-amber-50 p-6 text-amber-800">
          <h2 className="font-semibold">Отчёт не найден</h2>
          <p className="mt-2 text-sm">
            Сгенерируй labeled dataset и прогоняй оффлайн оценку:
          </p>
          <pre className="mt-3 rounded bg-amber-100 p-3 font-mono text-xs">
            python3 e2e-artifacts/seed_logs.py{"\n"}
            docker exec backend-api-1 python /app/e2e-artifacts/evaluate_detectors.py
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
          <h1 className="text-2xl font-bold text-slate-900">
            Сравнение детекторов аномалий
          </h1>
          <p className="mt-1 text-sm text-slate-500">
            Оценка на labeled synthetic dataset:{" "}
            <b>{data.dataset.points}</b> точек (service × minute),{" "}
            <b>{data.dataset.positives}</b> positive ·{" "}
            <b>{data.dataset.negatives}</b> negative
          </p>
        </div>
        <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-2 text-xs">
          <div className="flex items-center gap-1.5 text-amber-700">
            <Trophy className="h-3.5 w-3.5" />
            <span className="font-semibold uppercase tracking-wider">
              Лидер по PR-AUC
            </span>
          </div>
          <div className="mt-0.5 text-sm font-bold text-slate-900">
            {winner.name}{" "}
            <span className="font-mono text-amber-700">
              {winner.pr_auc.toFixed(4)}
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

      <div className="mt-8 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="mb-4 flex items-center gap-2">
          <BarChart3 className="h-4 w-4 text-slate-600" />
          <h2 className="text-sm font-semibold text-slate-900">
            Сводная таблица
          </h2>
        </div>
        <div className="overflow-hidden rounded-xl border border-slate-100">
          <table className="w-full">
            <thead className="bg-slate-50 text-xs font-semibold uppercase text-slate-500">
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
            <tbody className="divide-y divide-slate-100 text-sm">
              {data.results.map((r) => (
                <tr
                  key={r.name}
                  className={r.name === winner.name ? "bg-amber-50/40" : ""}
                >
                  <td className="px-4 py-2.5 font-medium text-slate-900">
                    {r.name === winner.name && "🏆 "}
                    {r.name}
                  </td>
                  <td className="px-4 py-2.5 text-right font-mono text-slate-700">
                    {r.roc_auc.toFixed(4)}
                  </td>
                  <td
                    className={cn(
                      "px-4 py-2.5 text-right font-mono",
                      r.name === winner.name
                        ? "font-bold text-amber-700"
                        : "text-slate-700"
                    )}
                  >
                    {r.pr_auc.toFixed(4)}
                  </td>
                  <td className="px-4 py-2.5 text-right font-mono text-slate-700">
                    {r.best.f1.toFixed(4)}
                  </td>
                  <td className="px-4 py-2.5 text-right font-mono text-slate-700">
                    {r.best.precision.toFixed(2)}
                  </td>
                  <td className="px-4 py-2.5 text-right font-mono text-slate-700">
                    {r.best.recall.toFixed(2)}
                  </td>
                  <td className="px-4 py-2.5 text-right font-mono text-slate-500">
                    {r.best.threshold.toFixed(2)}
                  </td>
                  <td className="px-4 py-2.5 text-right font-mono text-slate-700">
                    {r["at_threshold_3.5"].f1.toFixed(4)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="mt-6 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <h2 className="mb-3 text-sm font-semibold text-slate-900">
          Интерпретация
        </h2>
        <ul className="space-y-2 text-sm text-slate-700">
          <li>
            <b>ROC-AUC ~ 0.99 у всех</b> — на резком burst'е все методы
            ранжируют аномалии первыми, это не различительная метрика.
          </li>
          <li>
            <b>PR-AUC</b> показывает реальную разницу при несбалансированных
            классах ({data.dataset.positives} positives vs{" "}
            {data.dataset.negatives} negatives).{" "}
            <b>MAD z-score</b> лидирует.
          </li>
          <li>
            <b>Classic z-score</b> деградирует на baseline-шуме: редкие
            transient-ошибки раздувают σ, и score настоящего burst'а снижается.
          </li>
          <li>
            <b>Rolling stddev (15m)</b> — короткое окно не защищает от
            выбросов.
          </li>
          <li>
            <b>Isolation Forest</b> — сопоставимая ранжирующая способность
            (PR-AUC 0.84), но scores в другом диапазоне, единый порог 3.5
            неприменим без калибровки.
          </li>
          <li>
            <b>MAD z-score</b> устойчив к выбросам (медианные оценки), даёт
            <b> Precision = 1.0</b> на оптимальном пороге — это эмпирически
            подтверждает выбор именно MAD в production-цикле{" "}
            <code className="rounded bg-slate-100 px-1.5 py-0.5 font-mono text-xs">
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
        "rounded-2xl border bg-white p-5 shadow-sm",
        isWinner
          ? "border-amber-300 ring-2 ring-amber-100"
          : "border-slate-200"
      )}
    >
      <div className="mb-4 flex items-start justify-between">
        <div>
          <div className="flex items-center gap-2">
            {isWinner && <Trophy className="h-4 w-4 text-amber-500" />}
            <h3 className="font-semibold text-slate-900">{report.name}</h3>
          </div>
          <div className="mt-1 text-xs text-slate-500">
            оптимальный порог:{" "}
            <span className="font-mono">{report.best.threshold.toFixed(2)}</span>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1 text-xs">
            <CircleCheck className="h-3 w-3 text-emerald-500" />
            <span className="font-mono text-slate-700">
              TP={report.best.tp}
            </span>
          </div>
          <div className="flex items-center gap-1 text-xs">
            <CircleX className="h-3 w-3 text-red-500" />
            <span className="font-mono text-slate-700">
              FP={report.best.fp}
            </span>
          </div>
        </div>
      </div>

      <div className="space-y-3">
        <Bar label="PR-AUC" pct={prBar} value={report.pr_auc.toFixed(4)} />
        <Bar label="ROC-AUC" pct={rocBar} value={report.roc_auc.toFixed(4)} />
        <Bar
          label="F1 (best)"
          pct={f1Bar}
          value={report.best.f1.toFixed(4)}
        />
      </div>

      <div className="mt-4 grid grid-cols-2 gap-2 text-xs">
        <div className="rounded-lg bg-slate-50 px-3 py-2">
          <div className="text-slate-500">Precision</div>
          <div className="font-mono text-base font-bold text-slate-900">
            {report.best.precision.toFixed(2)}
          </div>
        </div>
        <div className="rounded-lg bg-slate-50 px-3 py-2">
          <div className="text-slate-500">Recall</div>
          <div className="font-mono text-base font-bold text-slate-900">
            {report.best.recall.toFixed(2)}
          </div>
        </div>
      </div>

      <div className="mt-3 flex items-center justify-between rounded-lg border border-slate-100 bg-slate-50 px-3 py-2 text-xs">
        <div>
          <Target className="mr-1 inline h-3 w-3 text-slate-400" />
          <span className="text-slate-500">На production-пороге 3.5:</span>
        </div>
        <span className="font-mono text-slate-700">
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
}: {
  label: string;
  pct: number;
  value: string;
}) {
  return (
    <div>
      <div className="mb-0.5 flex items-center justify-between text-xs">
        <span className="font-medium text-slate-700">{label}</span>
        <span className="font-mono text-slate-700">{value}</span>
      </div>
      <div className="h-2 overflow-hidden rounded-full bg-slate-100">
        <div
          className="h-full bg-gradient-to-r from-blue-500 to-purple-500"
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}
