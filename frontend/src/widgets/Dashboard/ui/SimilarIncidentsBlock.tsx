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
    <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="mb-4 flex items-center gap-2">
        <Link2 className="h-4 w-4 text-slate-600" />
        <h2 className="text-sm font-semibold text-slate-900">
          Похожие инциденты
        </h2>
        <span className="ml-auto text-[10px] text-slate-400">
          гибридный score
        </span>
      </div>

      {isLoading ? (
        <div className="py-4 text-center text-xs text-slate-400">загрузка…</div>
      ) : !data || data.matches.length === 0 ? (
        <div className="py-4 text-center text-xs text-slate-400">
          Похожих инцидентов не найдено
        </div>
      ) : (
        <div className="space-y-2">
          {data.matches.map((m) => {
            const inc = m.incident;
            const pct = Math.round(m.score * 100);
            return (
              <button
                key={m.incident_id}
                onClick={() => dispatch(selectIncident(m.incident_id))}
                className="flex w-full items-center gap-3 rounded-lg border border-slate-100 p-2 text-left transition hover:border-slate-300 hover:bg-slate-50"
              >
                <div className="flex w-10 flex-col items-center">
                  <div className="text-base font-bold text-slate-900">{pct}%</div>
                  <div className="text-[9px] text-slate-400">similarity</div>
                </div>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-1.5">
                    <span
                      className={cn(
                        "rounded px-1.5 py-0 text-[9px] font-semibold uppercase",
                        severityColors[inc.severity]
                      )}
                    >
                      {inc.severity}
                    </span>
                    <span className="truncate text-xs font-medium text-slate-900">
                      {truncate(inc.title, 50)}
                    </span>
                  </div>
                  <div className="mt-0.5 flex items-center gap-2 text-[10px] text-slate-500">
                    <span>{inc.service}</span>
                    <span>·</span>
                    <span>{inc.category}</span>
                    <span>·</span>
                    <span>root: {inc.root_cause_service || "?"}</span>
                  </div>
                </div>
                <span
                  className={cn(
                    "shrink-0 rounded px-1.5 py-0 text-[9px]",
                    statusColors[inc.status]
                  )}
                >
                  {statusLabel[inc.status]}
                </span>
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
};
