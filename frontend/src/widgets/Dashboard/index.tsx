import { useSelector } from "react-redux";
import type { RootState } from "@/lib/store";
import { Header } from "./ui/Header";
import { OverviewPage } from "./ui/OverviewPage";
import { IncidentsPage } from "./ui/IncidentsPage";

export const Dashboard = () => {
  const view = useSelector((s: RootState) => s.dashboardView.view);

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-200">
      <Header />
      <main>
        {view === "overview" && <OverviewPage />}
        {view === "incidents" && <IncidentsPage />}
      </main>
    </div>
  );
};
