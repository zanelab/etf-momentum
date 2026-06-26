import { Navigate, Route, Routes } from "react-router-dom";

import { Layout } from "@/layouts/Layout";
import { HealthPage } from "@/pages/HealthPage";

export function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<Navigate to="/health" replace />} />
        <Route path="health" element={<HealthPage />} />
        <Route path="*" element={<Navigate to="/health" replace />} />
      </Route>
    </Routes>
  );
}
