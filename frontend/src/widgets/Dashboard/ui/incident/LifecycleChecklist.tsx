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
      className={cn(
        "h-4 w-4 shrink-0",
        active
          ? "text-emerald-400 drop-shadow-[0_0_4px_rgba(52,211,153,0.5)]"
          : "text-zinc-700"
      )}
    />
    <div className="flex-1">
      <div
        className={cn(
          "font-mono text-xs",
          active ? "font-semibold text-zinc-100" : "text-zinc-600"
        )}
      >
        {label}
      </div>
      {active && time && (
        <div className="font-mono text-[10px] text-zinc-500">
          {formatDateTime(time)}
        </div>
      )}
    </div>
  </div>
);

export const LifecycleChecklist = ({ incident }: { incident: Incident }) => (
  <div className="rounded-xl border border-zinc-800/60 bg-zinc-900/40 p-5 backdrop-blur">
    <div className="mb-3 flex items-center gap-2">
      <div className="flex h-6 w-6 items-center justify-center rounded-md bg-emerald-500/10 ring-1 ring-emerald-500/30">
        <AlertCircle className="h-3.5 w-3.5 text-emerald-400" />
      </div>
      <h2 className="text-sm font-semibold text-zinc-100">Жизненный цикл</h2>
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
