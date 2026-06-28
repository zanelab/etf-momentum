// Top-level shell + routes.
import { Link, Route, Routes } from "react-router-dom";

import Backtest from "@/pages/Backtest";
import DataSource from "@/pages/DataSource";
import History from "@/pages/History";
import PoolConfig from "@/pages/PoolConfig";
import Portfolio from "@/pages/Portfolio";
import Signals from "@/pages/Signals";
import StrategyConfig from "@/pages/StrategyConfig";
import ThemeConfig from "@/pages/ThemeConfig";

const NAV = [
  { to: "/pool", label: "静态池" },
  { to: "/themes", label: "主题词典" },
  { to: "/strategy", label: "策略参数" },
  { to: "/signals", label: "当日信号" },
  { to: "/portfolio", label: "持仓" },
  { to: "/backtest", label: "回测" },
  { to: "/history", label: "历史数据" },
  { to: "/datasource", label: "数据源" },
];

export default function App() {
  return (
    <div className="min-h-screen bg-background text-foreground">
      <header className="border-b">
        <div className="container flex h-14 items-center gap-6">
          <h1 className="font-semibold">ETF Momentum</h1>
          <nav className="flex gap-4 text-sm">
            {NAV.map((n) => (
              <Link
                key={n.to}
                to={n.to}
                className="text-muted-foreground hover:text-foreground"
              >
                {n.label}
              </Link>
            ))}
          </nav>
        </div>
      </header>
      <main className="container py-6">
        <Routes>
          <Route path="/" element={<Landing />} />
          <Route path="/pool" element={<PoolConfig />} />
          <Route path="/themes" element={<ThemeConfig />} />
          <Route path="/strategy" element={<StrategyConfig />} />
          <Route path="/signals" element={<Signals />} />
          <Route path="/portfolio" element={<Portfolio />} />
          <Route path="/backtest" element={<Backtest />} />
          <Route path="/history" element={<History />} />
          <Route path="/datasource" element={<DataSource />} />
        </Routes>
      </main>
    </div>
  );
}

function Landing() {
  return (
    <section className="space-y-2">
      <h2 className="text-lg font-semibold">ETF 动量轮动（mock 全栈版）</h2>
      <p className="text-sm text-muted-foreground">
        后端使用 fixture CSV 作为行情源，前端通过 /api 与之通信。
        选择上方任一页面开始。
      </p>
      <ul className="ml-5 list-disc text-sm">
        {NAV.map((n) => (
          <li key={n.to}>
            <Link to={n.to} className="text-blue-600 hover:underline">
              {n.label}
            </Link>
          </li>
        ))}
      </ul>
    </section>
  );
}
