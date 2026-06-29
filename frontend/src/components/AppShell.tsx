import type { ReactNode } from "react";
import { Link, NavLink } from "react-router-dom";

const TOP_NAV: ReadonlyArray<{ to: string; label: string }> = [
  { to: "/", label: "仪表盘" },
  { to: "/portfolio", label: "持仓" },
  { to: "/signals", label: "今日调仓" },
];

interface AppShellProps {
  children: ReactNode;
  onSettingsClick?: () => void;
}

export function AppShell({ children, onSettingsClick }: AppShellProps) {
  return (
    <div className="min-h-screen bg-background text-foreground">
      <header className="border-b">
        <div className="container flex h-14 items-center gap-6">
          <Link to="/" className="font-semibold">
            <h1 className="font-semibold">ETF Momentum</h1>
          </Link>
          <nav className="flex gap-4 text-sm">
            {TOP_NAV.map((n) => (
              <NavLink
                key={n.to}
                to={n.to}
                end={n.to === "/"}
                className={({ isActive }) =>
                  isActive ? "text-foreground" : "text-muted-foreground hover:text-foreground"
                }
              >
                {n.label}
              </NavLink>
            ))}
            <button
              type="button"
              onClick={onSettingsClick}
              className="text-muted-foreground hover:text-foreground"
            >
              设置
            </button>
          </nav>
        </div>
      </header>
      <main className="container py-6">{children}</main>
    </div>
  );
}
