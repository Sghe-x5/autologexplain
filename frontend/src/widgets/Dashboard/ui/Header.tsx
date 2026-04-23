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
    <header className="sticky top-0 z-30 border-b border-slate-200 bg-white/90 backdrop-blur supports-[backdrop-filter]:bg-white/70">
      <div className="mx-auto flex h-16 max-w-7xl items-center gap-8 px-6">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-blue-600 to-purple-600 text-white shadow-sm">
            <Activity className="h-5 w-5" />
          </div>
          <div>
            <div className="text-sm font-semibold text-slate-900">
              AutoLogExplain
            </div>
            <div className="text-xs text-slate-500">
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
                  ? "bg-slate-900 text-white shadow-sm"
                  : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
              )}
              data-test-id={`dashboard-tab-${tab.id}`}
            >
              {tab.icon}
              {tab.label}
            </button>
          ))}
        </nav>

        <div className="ml-auto flex items-center gap-2">
          <div className="flex items-center gap-2 rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1 text-xs font-medium text-emerald-700">
            <div className="h-2 w-2 animate-pulse rounded-full bg-emerald-500" />
            API активен
          </div>
        </div>
      </div>
    </header>
  );
};
