/**
 * 4 meta-статистики инцидента: opened, impact, burn rate, root cause.
 */

import type { Incident } from "@/api/incidentsApi";
import { cn } from "@/lib/utils";
import {
  formatDateTime,
  formatNumber,
  formatRelativeTime,
} from "@/widgets/Dashboard/lib/format";

type HighlightTone = "red" | "amber" | undefined;

const MetaStat = ({
  label,
  value,
  sub,
  highlight,
}: {
  label: string;
  value: React.ReactNode;
  sub?: string;
  highlight?: HighlightTone;
}) => (
  <div className="rounded-xl border border-slate-100 bg-slate-50 px-3 py-2">
    <div className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">
      {label}
    </div>
    <div
      className={cn(
        "mt-0.5 text-lg font-bold",
        highlight === "red" && "text-red-600",
        highlight === "amber" && "text-amber-600",
        !highlight && "text-slate-900"
      )}
    >
      {value}
    </div>
    {sub && <div className="mt-0.5 text-[11px] text-slate-500">{sub}</div>}
  </div>
);

export const IncidentMetaStats = ({ incident }: { incident: Incident }) => {
  const burnTone: HighlightTone =
    incident.burn_rate_1h > 14.4 ? "red" : incident.burn_rate_1h > 6 ? "amber" : undefined;

  return (
    <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
      <MetaStat
        label="Открыт"
        value={formatRelativeTime(incident.opened_at)}
        sub={formatDateTime(incident.opened_at)}
      />
      <MetaStat
        label="Impact score"
        value={formatNumber(incident.impact_score, 2)}
        sub={`affected: ${incident.affected_services}`}
      />
      <MetaStat
        label="Burn rate 1h"
        value={`${formatNumber(incident.burn_rate_1h, 1)}×`}
        sub={`5m: ${formatNumber(incident.burn_rate_5m, 1)}× · 6h: ${formatNumber(
          incident.burn_rate_6h,
          1
        )}×`}
        highlight={burnTone}
      />
      <MetaStat
        label="Root cause (online)"
        value={incident.root_cause_service || "—"}
        sub={`score: ${formatNumber(incident.root_cause_score, 2)}`}
      />
    </div>
  );
};
