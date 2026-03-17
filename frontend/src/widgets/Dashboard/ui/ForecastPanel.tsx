import { Activity, TrendingUp, TrendingDown, Gauge, AlertTriangle } from "lucide-react";
import { useGetCurrentRiskQuery } from "@/api";
import { cn } from "@/lib/utils";
import { formatNumber } from "@/widgets/Dashboard/lib/format";

/**
 * Forecast Panel — показывает risk score + SHAP top-features для сервиса инцидента.
 * Встраивается в IncidentDetails.
 */
export const ForecastPanel = ({
  service,
  environment,
}: {
  service: string;
  environment: string;
}) => {
  const { data, isLoading, error } = useGetCurrentRiskQuery({ hours: 2 });

  if (isLoading) {
    return (
      <div className="rounded-xl border border-zinc-800/60 bg-zinc-900/40 p-5 backdrop-blur">
        <Header />
        <div className="py-4 text-center text-xs text-zinc-600">загрузка…</div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="rounded-xl border border-zinc-800/60 bg-zinc-900/40 p-5 backdrop-blur">
        <Header />
        <div className="py-4 text-center text-xs text-zinc-500">
          Модель не обучена. Запусти:
          <pre className="mt-1 rounded bg-zinc-950/60 px-2 py-1 font-mono text-[10px] text-zinc-400">
            docker exec backend-api-1 python -m backend.services.forecasting.trainer
          </pre>
        </div>
      </div>
    );
  }

  const mine = data.predictions.find(
    (p) => p.service === service && p.environment === environment
  );

  if (!mine) {
    return (
      <div className="rounded-xl border border-zinc-800/60 bg-zinc-900/40 p-5 backdrop-blur">
        <Header />
        <div className="py-4 text-center text-xs text-zinc-500">
          Нет данных по сервису <b className="text-zinc-300">{service}</b> в{" "}
          <b className="text-zinc-300">{environment}</b> за последние 2 часа
        </div>
      </div>
    );
  }

  const risk = mine.risk_score;
  const pct = Math.round(risk * 100);
  const tone =
    risk >= 0.7 ? "red" : risk >= 0.4 ? "amber" : risk >= 0.2 ? "blue" : "emerald";
  const labelMap = {
    red: "Высокий риск",
    amber: "Средний риск",
    blue: "Низкий риск",
    emerald: "Норма",
  } as const;
  const colorBar: Record<typeof tone, string> = {
    red: "bg-gradient-to-r from-rose-500 to-rose-400",
    amber: "bg-gradient-to-r from-amber-500 to-amber-400",
    blue: "bg-gradient-to-r from-sky-500 to-sky-400",
    emerald: "bg-gradient-to-r from-emerald-500 to-emerald-400",
  };
  const tonePill: Record<typeof tone, string> = {
    red: "bg-rose-500/10 text-rose-300 border-rose-500/30",
    amber: "bg-amber-500/10 text-amber-300 border-amber-500/30",
    blue: "bg-sky-500/10 text-sky-300 border-sky-500/30",
    emerald: "bg-emerald-500/10 text-emerald-300 border-emerald-500/30",
  };
  const toneText: Record<typeof tone, string> = {
    red: "text-rose-400",
    amber: "text-amber-400",
    blue: "text-sky-400",
    emerald: "text-emerald-400",
  };

  return (
    <div className="rounded-xl border border-zinc-800/60 bg-zinc-900/40 p-5 backdrop-blur">
      <Header />

      <div className="mb-4 flex items-start gap-4">
        <div className="flex-1">
          <div className="mb-1 flex items-center gap-2">
            <span
              className={cn(
                "rounded-md border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider",
                tonePill[tone]
              )}
            >
              ● {labelMap[tone]}
            </span>
            <span className="font-mono text-[11px] text-zinc-500">
              горизонт {data.horizon_minutes} мин
            </span>
          </div>
          <div className={cn("text-4xl font-bold tabular-nums", toneText[tone])}>
            {pct}%
          </div>
          <div className="text-xs text-zinc-500">
            P(инцидент в ближайшие {data.horizon_minutes} минут)
          </div>
        </div>

        <div className="w-32">
          <div className="mb-1 text-[10px] font-semibold uppercase tracking-wider text-zinc-500">
            Risk score
          </div>
          <div className="h-1.5 w-full overflow-hidden rounded-full bg-zinc-800">
            <div className={cn("h-full", colorBar[tone])} style={{ width: `${pct}%` }} />
          </div>
          <div className="mt-0.5 text-right font-mono text-[10px] text-zinc-500">
            {formatNumber(risk, 3)}
          </div>
        </div>
      </div>

      <div className="mt-4">
        <div className="mb-2 flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-wider text-zinc-500">
          <Gauge className="h-3 w-3" />
          Top-5 факторов (SHAP)
        </div>
        <div className="space-y-1.5">
          {mine.top_features.map((f) => (
            <FeatureRow
              key={f.name}
              name={f.name}
              value={f.value}
              shap={f.shap}
              direction={f.direction}
            />
          ))}
        </div>
      </div>
    </div>
  );
};

const Header = () => (
  <div className="mb-4 flex items-center gap-2">
    <div className="flex h-6 w-6 items-center justify-center rounded-md bg-violet-500/10 ring-1 ring-violet-500/30">
      <Activity className="h-3.5 w-3.5 text-violet-400" />
    </div>
    <h2 className="text-sm font-semibold text-zinc-100">Прогноз: риск инцидента</h2>
    <span className="ml-auto rounded-md bg-gradient-to-r from-indigo-500/15 to-violet-500/15 px-2 py-0.5 font-mono text-[10px] font-semibold text-indigo-300 ring-1 ring-indigo-500/30">
      XGBoost · SHAP
    </span>
  </div>
);

const FeatureRow = ({
  name,
  value,
  shap,
  direction,
}: {
  name: string;
  value: number;
  shap: number;
  direction: "up" | "down";
}) => {
  const up = direction === "up";
  const magn = Math.min(Math.abs(shap) / 3, 1);
  const pct = Math.round(magn * 100);

  return (
    <div className="flex items-center gap-2 font-mono text-xs">
      {up ? (
        <TrendingUp className="h-3 w-3 shrink-0 text-rose-400" />
      ) : (
        <TrendingDown className="h-3 w-3 shrink-0 text-emerald-400" />
      )}
      <code className="w-40 shrink-0 truncate text-[11px] text-zinc-300">
        {name}
      </code>
      <span className="shrink-0 text-[10px] text-zinc-500">= {value.toFixed(2)}</span>
      <div className="relative flex-1">
        <div className="h-1 w-full overflow-hidden rounded-full bg-zinc-800">
          <div
            className={cn(
              "h-full",
              up
                ? "bg-gradient-to-r from-rose-500 to-rose-400"
                : "bg-gradient-to-r from-emerald-500 to-emerald-400"
            )}
            style={{ width: `${pct}%` }}
          />
        </div>
      </div>
      <span
        className={cn(
          "w-14 shrink-0 text-right text-[10px] tabular-nums",
          up ? "text-rose-400" : "text-emerald-400"
        )}
      >
        {shap > 0 ? "+" : ""}
        {shap.toFixed(3)}
      </span>
    </div>
  );
};

/**
 * Небольшой helper — если есть серьёзный риск, показать alert-pill на inspector-блоке.
 */
export const RiskAlertPill = ({ risk }: { risk: number }) => {
  if (risk < 0.5) return null;
  return (
    <div className="inline-flex items-center gap-1 rounded-md border border-rose-500/30 bg-rose-500/10 px-2 py-0.5 text-[11px] font-semibold text-rose-300">
      <AlertTriangle className="h-3 w-3" />
      Риск {Math.round(risk * 100)}%
    </div>
  );
};
