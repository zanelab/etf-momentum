import { Link, Route, Routes } from "react-router-dom";

export default function App() {
  return (
    <div className="min-h-screen bg-background text-foreground">
      <header className="border-b">
        <div className="container flex h-14 items-center gap-6">
          <h1 className="font-semibold">ETF Momentum</h1>
          <nav className="flex gap-4 text-sm">
            <Link to="/pool">静态池</Link>
            <Link to="/themes">主题词典</Link>
            <Link to="/strategy">策略参数</Link>
            <Link to="/signals">当日信号</Link>
            <Link to="/portfolio">持仓</Link>
            <Link to="/backtest">回测</Link>
            <Link to="/history">历史数据</Link>
          </nav>
        </div>
      </header>
      <main className="container py-6">
        <Routes>
          <Route path="/" element={<p>请选择一个页面</p>} />
          <Route path="/pool" element={<p>静态池配置（待实现）</p>} />
          <Route path="/themes" element={<p>主题词典配置（待实现）</p>} />
          <Route path="/strategy" element={<p>策略参数配置（待实现）</p>} />
          <Route path="/signals" element={<p>当日信号（待实现）</p>} />
          <Route path="/portfolio" element={<p>持仓（待实现）</p>} />
          <Route path="/backtest" element={<p>回测（待实现）</p>} />
          <Route path="/history" element={<p>历史数据（待实现）</p>} />
        </Routes>
      </main>
    </div>
  );
}