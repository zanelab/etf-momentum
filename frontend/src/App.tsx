import { Navigate, Route, Routes } from "react-router-dom";

import { Layout } from "@/layouts/Layout";
import { BacktestPage } from "@/pages/BacktestPage";
import { DashboardPage } from "@/pages/DashboardPage";
import { HealthPage } from "@/pages/HealthPage";
import { PoolsPage } from "@/pages/PoolsPage";

export function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<Navigate to="/dashboard" replace />} />
        <Route path="dashboard" element={<DashboardPage />} />
        <Route path="pools" element={<PoolsPage />} />
        <Route path="backtest" element={<BacktestPage />} />
        <Route path="health" element={<HealthPage />} />
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Route>
    </Routes>
  );
}
