/**
 * Lifecycle checkpoints: opened → acknowledged → mitigated → resolved.
 * Галочка + время, когда фаза достигнута.
 */

import { AlertCircle, CheckCircle2 } from "lucide-react";
import type { Incident } from "@/api/incidentsApi";
import { formatDateTime } from "@/widgets/Dashboard/lib/format";
import { cn } from "@/lib/utils";

const Pill = ({
  active,
  label,
  time,
}: {
  active: boolean;
  label: string;
  time: string | null | undefined;
}) => (
  <div className="flex items-center gap-2 py-1.5">
    <CheckCircle2
      className={cn("h-4 w-4", active ? "text-emerald-500" : "text-slate-300")}
    />
    <div className="flex-1">
      <div
        className={cn(
          "text-xs font-medium",
          active ? "text-slate-900" : "text-slate-400"
        )}
      >
        {label}
      </div>
      {active && time && (
        <div className="text-[10px] text-slate-500">{formatDateTime(time)}</div>
      )}
    </div>
  </div>
);

export const LifecycleChecklist = ({ incident }: { incident: Incident }) => (
  <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
    <div className="mb-3 flex items-center gap-2">
      <AlertCircle className="h-4 w-4 text-slate-600" />
      <h2 className="text-sm font-semibold text-slate-900">Жизненный цикл</h2>
    </div>
    <Pill active={!!incident.opened_at} label="open" time={incident.opened_at} />
    <Pill
      active={!!incident.acknowledged_at}
      label="acknowledged"
      time={incident.acknowledged_at}
    />
    <Pill
      active={!!incident.mitigated_at}
      label="mitigated"
      time={incident.mitigated_at}
    />
    <Pill
      active={!!incident.resolved_at}
      label="resolved"
      time={incident.resolved_at}
    />
  </div>
);
