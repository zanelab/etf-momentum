import { useCallback, useState } from "react";
import { Navigate, Route, Routes } from "react-router-dom";

import { AppShell } from "@/components/AppShell";
import { Sidebar } from "@/components/Sidebar";
import Backtest from "@/pages/Backtest";
import Dashboard from "@/pages/Dashboard";
import DataSource from "@/pages/DataSource";
import DynamicPoolPage from "@/pages/DynamicPoolPage";
import EtfDetailPage from "@/pages/EtfDetailPage";
import PoolConfig from "@/pages/PoolConfig";
import PortfolioSettingsPage from "@/pages/PortfolioSettingsPage";
import StrategyConfig from "@/pages/StrategyConfig";
import ThemeConfig from "@/pages/ThemeConfig";

export default function App() {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  // Stable callback refs so Sidebar's keydown effect doesn't re-bind on every
  // render of this component.
  const openSidebar = useCallback(() => setSidebarOpen(true), []);
  const closeSidebar = useCallback(() => setSidebarOpen(false), []);

  return (
    <>
      <AppShell onSettingsClick={openSidebar}>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/pool" element={<PoolConfig />} />
          <Route path="/portfolio" element={<PortfolioSettingsPage />} />
          <Route path="/themes" element={<ThemeConfig />} />
          <Route path="/strategy" element={<StrategyConfig />} />
          <Route path="/dynamic-pool" element={<DynamicPoolPage />} />
          <Route path="/dynamic-pool/:code" element={<EtfDetailPage />} />
          <Route path="/backtest" element={<Backtest />} />
          <Route path="/datasource" element={<DataSource />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AppShell>
      <Sidebar open={sidebarOpen} onClose={closeSidebar} />
    </>
  );
}
