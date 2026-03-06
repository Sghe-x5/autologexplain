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
    <div className="mb-6 rounded-xl border border-zinc-800/60 bg-zinc-900/40 p-6 backdrop-blur">
      <div className="flex flex-wrap items-start gap-4">
        <div className="min-w-0 flex-1">
          <div className="mb-2 flex items-center gap-2">
            <SeverityBadge value={incident.severity} />
            <StatusBadge value={incident.status} />
            <span className="font-mono text-[11px] text-zinc-500">
              {incident.service} · {incident.environment} · {incident.category}
            </span>
          </div>
          <h1 className="text-xl font-bold text-zinc-50">{incident.title}</h1>
          <div className="mt-1 font-mono text-xs text-zinc-600">
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
              className="rounded-lg border border-zinc-700 bg-zinc-800/60 px-3 py-1.5 text-xs font-medium text-zinc-300 transition hover:border-violet-500/40 hover:bg-zinc-800 hover:text-violet-300 disabled:opacity-50"
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
