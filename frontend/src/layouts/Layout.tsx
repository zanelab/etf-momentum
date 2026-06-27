import { Activity } from "lucide-react";
import { NavLink, Outlet } from "react-router-dom";

import { cn } from "@/lib/utils";

const navItems = [
  { to: "/dashboard", label: "动量看板" },
  { to: "/pools", label: "策略池" },
  { to: "/backtest", label: "回测" },
  { to: "/health", label: "健康检查" },
];

export function Layout() {
  return (
    <div className="flex min-h-screen bg-background text-foreground">
      <aside className="w-56 border-r bg-secondary/30 p-4">
        <div className="mb-6 flex items-center gap-2">
          <Activity className="h-5 w-5 text-primary" />
          <span className="font-semibold">etf-momentum</span>
        </div>
        <nav className="flex flex-col gap-1">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                cn(
                  "rounded-md px-3 py-2 text-sm transition-colors",
                  isActive
                    ? "bg-primary text-primary-foreground"
                    : "hover:bg-accent hover:text-accent-foreground",
                )
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
      </aside>
      <div className="flex flex-1 flex-col">
        <header className="border-b bg-background px-6 py-3">
          <h1 className="text-lg font-medium">A 股 ETF 动量策略系统</h1>
        </header>
        <main className="flex-1 p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
