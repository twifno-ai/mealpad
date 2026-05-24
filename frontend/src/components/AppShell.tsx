import { Outlet } from "react-router-dom";
import OfflineBanner from "./OfflineBanner";
import TabBar from "./TabBar";

export default function AppShell() {
  return (
    <div className="app-shell">
      <OfflineBanner />
      <main className="app-shell-main">
        <Outlet />
      </main>
      <TabBar />
    </div>
  );
}
