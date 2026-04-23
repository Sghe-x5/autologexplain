import { useSelector } from "react-redux";
import type { RootState } from "@/lib/store";
import { Header } from "./ui/Header";
import { OverviewPage } from "./ui/OverviewPage";
import { IncidentsPage } from "./ui/IncidentsPage";
import { GraphPage } from "./ui/GraphPage";
import { MetricsPage } from "./ui/MetricsPage";

export const Dashboard = () => {
  const view = useSelector((s: RootState) => s.dashboardView.view);

  return (
    <div className="min-h-screen bg-slate-50">
      <Header />
      <main>
        {view === "overview" && <OverviewPage />}
        {view === "incidents" && <IncidentsPage />}
        {view === "graph" && <GraphPage />}
        {view === "metrics" && <MetricsPage />}
      </main>
    </div>
  );
};
