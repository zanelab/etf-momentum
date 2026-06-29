import { useState } from "react";
import { Navigate, Route, Routes } from "react-router-dom";

import { AppShell } from "@/components/AppShell";
import { Sidebar } from "@/components/Sidebar";
import Backtest from "@/pages/Backtest";
import Dashboard from "@/pages/Dashboard";
import DataSource from "@/pages/DataSource";
import DynamicPoolPage from "@/pages/DynamicPoolPage";
import History from "@/pages/History";
import PoolConfig from "@/pages/PoolConfig";
import Portfolio from "@/pages/Portfolio";
import Signals from "@/pages/Signals";
import StrategyConfig from "@/pages/StrategyConfig";
import ThemeConfig from "@/pages/ThemeConfig";

export default function App() {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <>
      <AppShell onSettingsClick={() => setSidebarOpen(true)}>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/portfolio" element={<Portfolio />} />
          <Route path="/signals" element={<Signals />} />
          <Route path="/pool" element={<PoolConfig />} />
          <Route path="/themes" element={<ThemeConfig />} />
          <Route path="/strategy" element={<StrategyConfig />} />
          <Route path="/dynamic-pool" element={<DynamicPoolPage />} />
          <Route path="/backtest" element={<Backtest />} />
          <Route path="/history" element={<History />} />
          <Route path="/datasource" element={<DataSource />} />
          <Route path="/screening" element={<Navigate to="/signals" replace />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AppShell>
      <Sidebar open={sidebarOpen} onClose={() => setSidebarOpen(false)} />
    </>
  );
}
