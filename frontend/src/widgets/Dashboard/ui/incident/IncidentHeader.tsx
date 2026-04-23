/**
 * Хедер карточки инцидента: title, severity/status/meta, кнопки смены
 * статуса (только легальные переходы по FSM).
 */

import type { Incident, IncidentStatus } from "@/api/incidentsApi";
import { SeverityBadge, StatusBadge } from "@/components/ui/badges";
import { useUpdateStatusMutation } from "@/api";
import { statusLabel } from "@/widgets/Dashboard/lib/format";

const ALLOWED_NEXT: Record<IncidentStatus, IncidentStatus[]> = {
  open: ["acknowledged", "mitigated", "resolved"],
  acknowledged: ["mitigated", "resolved"],
  mitigated: ["resolved", "reopened"],
  resolved: ["reopened"],
  reopened: ["acknowledged", "mitigated", "resolved"],
};

export const IncidentHeader = ({ incident }: { incident: Incident }) => {
  const [updateStatus, updateResult] = useUpdateStatusMutation();
  const nextStatuses = ALLOWED_NEXT[incident.status] ?? [];

  return (
    <div className="mb-6 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
      <div className="flex flex-wrap items-start gap-4">
        <div className="min-w-0 flex-1">
          <div className="mb-2 flex items-center gap-2">
            <SeverityBadge value={incident.severity} />
            <StatusBadge value={incident.status} />
            <span className="text-[11px] text-slate-400">
              {incident.service} · {incident.environment} · {incident.category}
            </span>
          </div>
          <h1 className="text-xl font-bold text-slate-900">{incident.title}</h1>
          <div className="mt-1 font-mono text-xs text-slate-400">
            {incident.fingerprint}
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {nextStatuses.map((next) => (
            <button
              key={next}
              disabled={updateResult.isLoading}
              onClick={() =>
                updateStatus({
                  id: incident.incident_id,
                  status: next,
                  actor: "dashboard-user",
                })
              }
              className="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 transition hover:border-slate-400 hover:bg-slate-50 disabled:opacity-50"
              data-test-id={`status-transition-${next}`}
            >
              → {statusLabel[next]}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
};
