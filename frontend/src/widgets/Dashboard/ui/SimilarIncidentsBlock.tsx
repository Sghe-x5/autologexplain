import { Link2 } from "lucide-react";
import { useDispatch } from "react-redux";
import { useGetSimilarQuery } from "@/api";
import type { AppDispatch } from "@/lib/store";
import { selectIncident } from "@/widgets/Dashboard/model/viewSlice";
import {
  severityColors,
  statusColors,
  statusLabel,
  truncate,
} from "@/widgets/Dashboard/lib/format";
import { cn } from "@/lib/utils";

/**
 * Similar Incidents — top-k похожих инцидентов по гибридному скорингу.
 * Клик по строке — переход к инциденту.
 */
export const SimilarIncidentsBlock = ({ incidentId }: { incidentId: string }) => {
  const dispatch = useDispatch<AppDispatch>();
  const { data, isLoading } = useGetSimilarQuery({ id: incidentId, k: 5 });

  return (
    <div className="rounded-xl border border-zinc-800/60 bg-zinc-900/40 p-5 backdrop-blur">
      <div className="mb-4 flex items-center gap-2">
        <div className="flex h-6 w-6 items-center justify-center rounded-md bg-indigo-500/10 ring-1 ring-indigo-500/30">
          <Link2 className="h-3.5 w-3.5 text-indigo-300" />
        </div>
        <h2 className="text-sm font-semibold text-zinc-100">
          Похожие инциденты
        </h2>
        <span className="ml-auto font-mono text-[10px] text-zinc-500">
          гибридный score
        </span>
      </div>

      {isLoading ? (
        <div className="py-4 text-center text-xs text-zinc-600">загрузка…</div>
      ) : !data || data.matches.length === 0 ? (
        <div className="py-4 text-center text-xs text-zinc-600">
          Похожих инцидентов не найдено
        </div>
      ) : (
        <div className="space-y-1.5">
          {data.matches.map((m) => {
            const inc = m.incident;
            const pct = Math.round(m.score * 100);
            const scoreColor =
              pct >= 80
                ? "text-emerald-400"
                : pct >= 50
                ? "text-amber-400"
                : "text-zinc-400";
            return (
              <button
                key={m.incident_id}
                onClick={() => dispatch(selectIncident(m.incident_id))}
                className="flex w-full items-center gap-3 rounded-lg border border-zinc-800/60 bg-zinc-950/40 p-2.5 text-left transition hover:border-violet-500/40 hover:bg-zinc-900"
              >
                <div className="flex w-12 shrink-0 flex-col items-center">
                  <div className={cn("font-mono text-base font-bold tabular-nums", scoreColor)}>
                    {pct}%
                  </div>
                  <div className="text-[9px] uppercase tracking-wider text-zinc-600">
                    match
                  </div>
                </div>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-1.5">
                    <span
                      className={cn(
                        "rounded px-1.5 py-0 text-[9px] font-bold uppercase tracking-wider",
                        severityColors[inc.severity]
                      )}
                    >
                      ● {inc.severity}
                    </span>
                    <span className="truncate text-xs font-medium text-zinc-100">
                      {truncate(inc.title, 50)}
                    </span>
                  </div>
                  <div className="mt-0.5 flex items-center gap-1.5 font-mono text-[10px] text-zinc-500">
                    <span>{inc.service}</span>
                    <span className="text-zinc-700">·</span>
                    <span>{inc.category}</span>
                    <span className="text-zinc-700">·</span>
                    <span>
                      root:{" "}
                      <span className="text-violet-400">
                        {inc.root_cause_service || "?"}
                      </span>
                    </span>
                  </div>
                </div>
                <span
                  className={cn(
                    "shrink-0 rounded px-1.5 py-0.5 text-[9px] font-medium uppercase tracking-wider",
                    statusColors[inc.status]
                  )}
                >
                  {statusLabel[inc.status].toLowerCase()}
                </span>
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
};
