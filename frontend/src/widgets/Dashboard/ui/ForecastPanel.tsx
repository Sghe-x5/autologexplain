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
      <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <Header />
        <div className="py-4 text-center text-xs text-slate-400">загрузка…</div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <Header />
        <div className="py-4 text-center text-xs text-slate-400">
          Модель не обучена. Запусти:
          <pre className="mt-1 text-[10px]">docker exec backend-api-1 python -m backend.services.forecasting.trainer</pre>
        </div>
      </div>
    );
  }

  const mine = data.predictions.find(
    (p) => p.service === service && p.environment === environment
  );

  if (!mine) {
    return (
      <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <Header />
        <div className="py-4 text-center text-xs text-slate-400">
          Нет данных по сервису <b>{service}</b> в <b>{environment}</b> за последние 2 часа
        </div>
      </div>
    );
  }

  const risk = mine.risk_score;
  const pct = Math.round(risk * 100);
  const tone =
    risk >= 0.7 ? "red" : risk >= 0.4 ? "amber" : risk >= 0.2 ? "blue" : "emerald";
  const labelMap = { red: "Высокий риск", amber: "Средний риск", blue: "Низкий риск", emerald: "Норма" } as const;
  const colorBar: Record<typeof tone, string> = {
    red: "bg-red-500",
    amber: "bg-amber-500",
    blue: "bg-blue-500",
    emerald: "bg-emerald-500",
  };
  const tonePill: Record<typeof tone, string> = {
    red: "bg-red-100 text-red-800 border-red-200",
    amber: "bg-amber-100 text-amber-800 border-amber-200",
    blue: "bg-blue-50 text-blue-700 border-blue-100",
    emerald: "bg-emerald-50 text-emerald-700 border-emerald-100",
  };

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <Header />

      <div className="mb-4 flex items-start gap-4">
        <div className="flex-1">
          <div className="mb-1 flex items-center gap-2">
            <span
              className={cn(
                "rounded-md border px-2 py-0.5 text-[11px] font-semibold",
                tonePill[tone]
              )}
            >
              {labelMap[tone]}
            </span>
            <span className="text-[11px] text-slate-500">
              горизонт {data.horizon_minutes} минут
            </span>
          </div>
          <div className="text-3xl font-bold text-slate-900">{pct}%</div>
          <div className="text-xs text-slate-500">
            P(инцидент в ближайшие {data.horizon_minutes} минут)
          </div>
        </div>

        <div className="w-32">
          <div className="mb-1 text-[10px] font-medium text-slate-500">Risk score</div>
          <div className="h-3 w-full overflow-hidden rounded-full bg-slate-100">
            <div className={cn("h-full", colorBar[tone])} style={{ width: `${pct}%` }} />
          </div>
          <div className="mt-0.5 text-right font-mono text-[10px] text-slate-400">
            {formatNumber(risk, 3)}
          </div>
        </div>
      </div>

      <div className="mt-4">
        <div className="mb-2 flex items-center gap-1.5 text-xs font-semibold text-slate-700">
          <Gauge className="h-3 w-3" />
          Top-5 факторов (SHAP)
        </div>
        <div className="space-y-1.5">
          {mine.top_features.map((f) => (
            <FeatureRow key={f.name} name={f.name} value={f.value} shap={f.shap} direction={f.direction} />
          ))}
        </div>
      </div>
    </div>
  );
};

const Header = () => (
  <div className="mb-4 flex items-center gap-2">
    <Activity className="h-4 w-4 text-slate-600" />
    <h2 className="text-sm font-semibold text-slate-900">Прогноз: риск инцидента</h2>
    <span className="ml-auto rounded-md bg-gradient-to-r from-blue-100 to-purple-100 px-2 py-0.5 text-[10px] font-semibold text-blue-800">
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
  const magn = Math.min(Math.abs(shap) / 3, 1); // normalize
  const pct = Math.round(magn * 100);

  return (
    <div className="flex items-center gap-2 text-xs">
      {up ? (
        <TrendingUp className="h-3 w-3 shrink-0 text-red-500" />
      ) : (
        <TrendingDown className="h-3 w-3 shrink-0 text-emerald-500" />
      )}
      <code className="w-40 shrink-0 truncate font-mono text-[11px] text-slate-700">
        {name}
      </code>
      <span className="shrink-0 text-[10px] text-slate-500">= {value.toFixed(2)}</span>
      <div className="relative flex-1">
        <div className="h-1.5 w-full overflow-hidden rounded-full bg-slate-100">
          <div
            className={cn("h-full", up ? "bg-red-400" : "bg-emerald-400")}
            style={{ width: `${pct}%` }}
          />
        </div>
      </div>
      <span
        className={cn(
          "shrink-0 w-14 text-right font-mono text-[10px]",
          up ? "text-red-600" : "text-emerald-600"
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
 * Пока не используется, но зарезервировано на будущее.
 */
export const RiskAlertPill = ({ risk }: { risk: number }) => {
  if (risk < 0.5) return null;
  return (
    <div className="inline-flex items-center gap-1 rounded-md bg-red-50 px-2 py-0.5 text-[11px] font-semibold text-red-700">
      <AlertTriangle className="h-3 w-3" />
      Риск {Math.round(risk * 100)}%
    </div>
  );
};
