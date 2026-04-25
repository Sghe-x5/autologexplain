import { useDispatch, useSelector } from "react-redux";
import { Activity, BarChart3, LayoutDashboard, Network } from "lucide-react";
import { cn } from "@/lib/utils";
import type { AppDispatch, RootState } from "@/lib/store";
import {
  setView,
  type DashboardView,
} from "@/widgets/Dashboard/model/viewSlice";

const tabs: { id: DashboardView; label: string; icon: React.ReactNode }[] = [
  {
    id: "overview",
    label: "Обзор",
    icon: <LayoutDashboard className="h-4 w-4" />,
  },
  {
    id: "incidents",
    label: "Инциденты",
    icon: <Activity className="h-4 w-4" />,
  },
  {
    id: "graph",
    label: "Граф зависимостей",
    icon: <Network className="h-4 w-4" />,
  },
  {
    id: "metrics",
    label: "Метрики ML",
    icon: <BarChart3 className="h-4 w-4" />,
  },
];

export const Header = () => {
  const view = useSelector((s: RootState) => s.dashboardView.view);
  const dispatch = useDispatch<AppDispatch>();

  return (
    <header className="sticky top-0 z-30 border-b border-zinc-800/80 bg-zinc-950/90 backdrop-blur supports-[backdrop-filter]:bg-zinc-950/70">
      <div className="mx-auto flex h-16 max-w-7xl items-center gap-8 px-6">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-500 to-violet-600 text-white shadow-lg shadow-violet-500/20">
            <Activity className="h-5 w-5" />
          </div>
          <div>
            <div className="text-sm font-semibold text-zinc-100">
              AutoLogExplain
            </div>
            <div className="text-xs text-zinc-500">
              Автоматическая интерпретация логов
            </div>
          </div>
        </div>

        <nav className="flex items-center gap-1">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => dispatch(setView(tab.id))}
              className={cn(
                "inline-flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                view === tab.id
                  ? "bg-zinc-800/80 text-zinc-50 shadow-inner ring-1 ring-zinc-700"
                  : "text-zinc-400 hover:bg-zinc-900 hover:text-zinc-100"
              )}
              data-test-id={`dashboard-tab-${tab.id}`}
            >
              {tab.icon}
              {tab.label}
            </button>
          ))}
        </nav>

        <div className="ml-auto flex items-center gap-2">
          <div className="flex items-center gap-2 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-3 py-1 text-xs font-medium text-emerald-400">
            <div className="h-2 w-2 animate-pulse rounded-full bg-emerald-400 shadow-[0_0_8px_2px_rgba(52,211,153,0.6)]" />
            API активен
          </div>
        </div>
      </div>
    </header>
  );
};
