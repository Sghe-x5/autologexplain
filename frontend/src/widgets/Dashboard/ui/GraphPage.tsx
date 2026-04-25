import { useMemo } from "react";
import { Network, FileText } from "lucide-react";
import {
  useGetDependencyGraphQuery,
  useGetLogTemplatesQuery,
} from "@/api";
import { cn } from "@/lib/utils";

export const GraphPage = () => {
  const graph = useGetDependencyGraphQuery({ hours: 24, min_weight: 1 });
  const templates = useGetLogTemplatesQuery({ hours: 4, top_n: 10 });

  const { nodes, edges } = graph.data ?? { nodes: [], edges: [] };

  const layout = useMemo(() => computeLayout(nodes), [nodes]);

  return (
    <div className="mx-auto max-w-7xl px-6 py-8">
      <div className="mb-6">
        <h1 className="flex items-center gap-3 text-2xl font-bold text-zinc-50">
          <span className="inline-block h-5 w-1 rounded-sm bg-violet-500" />
          Граф зависимостей сервисов
        </h1>
        <p className="mt-1 text-sm text-zinc-500">
          Построен автоматически из trace_id в логах. Толщина ребра ∝ числу
          совместных трейсов.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2 rounded-xl border border-zinc-800/60 bg-zinc-900/40 p-5 backdrop-blur">
          <div className="mb-4 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="flex h-6 w-6 items-center justify-center rounded-md bg-violet-500/10 ring-1 ring-violet-500/30">
                <Network className="h-3.5 w-3.5 text-violet-400" />
              </div>
              <h2 className="text-sm font-semibold text-zinc-100">
                Топология
              </h2>
            </div>
            <div className="font-mono text-xs text-zinc-500">
              {nodes.length} узлов · {edges.length} рёбер
            </div>
          </div>

          {graph.isLoading ? (
            <div className="py-16 text-center text-sm text-zinc-600">
              загрузка…
            </div>
          ) : nodes.length === 0 ? (
            <div className="rounded-lg border border-dashed border-zinc-800 bg-zinc-950/40 py-16 text-center text-sm text-zinc-600">
              Нет trace_id в логах — граф пустой
            </div>
          ) : (
            <GraphSvg layout={layout} edges={edges} />
          )}

          <div className="mt-3 flex flex-wrap items-center gap-3 font-mono text-[11px] text-zinc-500">
            <span className="flex items-center gap-1.5">
              <span className="inline-block h-1 w-4 rounded-full bg-violet-500/40" />
              тонкое (weight 1-30)
            </span>
            <span className="flex items-center gap-1.5">
              <span className="inline-block h-[3px] w-4 rounded-full bg-violet-500/70" />
              среднее (30-100)
            </span>
            <span className="flex items-center gap-1.5">
              <span className="inline-block h-[5px] w-4 rounded-full bg-violet-400" />
              толстое (100+)
            </span>
          </div>
        </div>

        <div className="rounded-xl border border-zinc-800/60 bg-zinc-900/40 p-5 backdrop-blur">
          <div className="mb-4 flex items-center gap-2">
            <div className="flex h-6 w-6 items-center justify-center rounded-md bg-violet-500/10 ring-1 ring-violet-500/30">
              <FileText className="h-3.5 w-3.5 text-violet-400" />
            </div>
            <h2 className="text-sm font-semibold text-zinc-100">
              Топ-10 шаблонов
            </h2>
          </div>
          {templates.isLoading ? (
            <div className="py-10 text-center text-sm text-zinc-600">
              загрузка…
            </div>
          ) : (
            <div className="space-y-1.5">
              {(templates.data?.templates ?? []).map((t, i) => (
                <div
                  key={i}
                  className="rounded-lg border border-zinc-800/60 bg-zinc-950/60 p-2"
                >
                  <div className="mb-1 flex items-center justify-between font-mono text-[10px] text-zinc-500">
                    <span className="text-violet-400">#{i + 1}</span>
                    <span className="tabular-nums">{t.count}</span>
                  </div>
                  <code className="block break-words font-mono text-[11px] text-zinc-200">
                    {t.template}
                  </code>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      <div className="mt-6 rounded-xl border border-zinc-800/60 bg-zinc-900/40 p-5 backdrop-blur">
        <h2 className="mb-3 text-sm font-semibold text-zinc-100">
          Рёбра (отсортированы по весу)
        </h2>
        {edges.length === 0 ? (
          <div className="py-4 text-sm text-zinc-600">нет данных</div>
        ) : (
          <div className="overflow-hidden rounded-lg border border-zinc-800/60">
            <table className="w-full">
              <thead className="bg-zinc-950/60 text-[10px] font-semibold uppercase tracking-wider text-zinc-500">
                <tr>
                  <th className="px-3 py-2 text-left">Откуда</th>
                  <th className="px-3 py-2 text-left">Куда</th>
                  <th className="px-3 py-2 text-right">Вес (трейсов)</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-800/60 text-sm">
                {[...edges]
                  .sort((a, b) => b.weight - a.weight)
                  .map((e, i) => (
                    <tr key={i} className="transition hover:bg-zinc-900/40">
                      <td className="px-3 py-1.5 font-mono text-zinc-300">
                        {e.from}
                      </td>
                      <td className="px-3 py-1.5 font-mono text-zinc-300">
                        <span className="text-zinc-600">→</span> {e.to}
                      </td>
                      <td className="px-3 py-1.5 text-right font-mono font-semibold tabular-nums text-violet-400">
                        {e.weight}
                      </td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};

function computeLayout(
  nodes: string[]
): { x: number; y: number; name: string }[] {
  const n = nodes.length;
  if (n === 0) return [];
  const cx = 300;
  const cy = 220;
  const radius = Math.min(200, 60 + n * 20);
  return nodes.map((name, i) => {
    const angle = (i / n) * 2 * Math.PI - Math.PI / 2;
    return {
      name,
      x: cx + radius * Math.cos(angle),
      y: cy + radius * Math.sin(angle),
    };
  });
}

function GraphSvg({
  layout,
  edges,
}: {
  layout: { x: number; y: number; name: string }[];
  edges: { from: string; to: string; weight: number }[];
}) {
  const byName = new Map(layout.map((n) => [n.name, n]));
  const maxW = Math.max(1, ...edges.map((e) => e.weight));

  return (
    <svg
      viewBox="0 0 600 440"
      className="mx-auto block h-[440px] w-full"
      preserveAspectRatio="xMidYMid meet"
    >
      <defs>
        <marker
          id="arrow"
          viewBox="0 0 10 10"
          refX="9"
          refY="5"
          markerWidth="6"
          markerHeight="6"
          orient="auto"
        >
          <path d="M0,0 L10,5 L0,10 z" fill="#a855f7" />
        </marker>
      </defs>
      {edges.map((e, i) => {
        const a = byName.get(e.from);
        const b = byName.get(e.to);
        if (!a || !b) return null;
        const thickness =
          e.weight >= 100 ? 5 : e.weight >= 30 ? 3 : 1;
        const color =
          e.weight >= 100 ? "#a855f7" : e.weight >= 30 ? "#8b5cf6" : "#6366f1";
        const opacity = 0.4 + 0.6 * (e.weight / maxW);
        return (
          <line
            key={i}
            x1={a.x}
            y1={a.y}
            x2={b.x}
            y2={b.y}
            stroke={color}
            strokeWidth={thickness}
            opacity={opacity}
            markerEnd="url(#arrow)"
          />
        );
      })}
      {layout.map((n, i) => (
        <g key={i} transform={`translate(${n.x}, ${n.y})`}>
          <circle
            r={34}
            fill="#18181b"
            stroke="#a855f7"
            strokeWidth={1.5}
            opacity={0.95}
          />
          <circle
            r={34}
            fill="none"
            stroke="#a855f7"
            strokeWidth={0.5}
            opacity={0.3}
          />
          <text
            textAnchor="middle"
            dy="0.35em"
            className={cn(
              "font-mono font-semibold",
              n.name.length > 9 ? "text-[9px]" : "text-[11px]"
            )}
            fill="#e4e4e7"
          >
            {n.name}
          </text>
        </g>
      ))}
    </svg>
  );
}
