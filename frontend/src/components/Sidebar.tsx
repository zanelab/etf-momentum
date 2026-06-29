import { useEffect } from "react";
import { Link, useLocation } from "react-router-dom";

const CONFIG_ENTRIES = [
  { to: "/pool", label: "静态池" },
  { to: "/themes", label: "主题词典" },
  { to: "/strategy", label: "策略参数" },
  { to: "/dynamic-pool", label: "动态池" },
] as const;

const TOOL_ENTRIES = [
  { to: "/backtest", label: "回测" },
  { to: "/history", label: "历史数据" },
  { to: "/datasource", label: "数据源" },
] as const;

interface SidebarProps {
  open: boolean;
  onClose: () => void;
}

export function Sidebar({ open, onClose }: SidebarProps) {
  const location = useLocation();

  useEffect(() => {
    if (!open) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <>
      <div
        data-testid="sidebar-backdrop"
        onClick={onClose}
        className="fixed inset-0 z-40 bg-black/40"
      />
      <aside
        className="fixed left-0 top-0 z-50 h-full w-64 border-r bg-background shadow-lg"
        role="dialog"
        aria-label="设置"
      >
        <div className="flex h-14 items-center border-b px-4 font-semibold">设置</div>
        <nav className="flex flex-col p-2 text-sm">
          {CONFIG_ENTRIES.map((e) => (
            <SidebarLink key={e.to} to={e.to} label={e.label} active={location.pathname === e.to} onClose={onClose} />
          ))}
          <div className="my-2 border-t" />
          {TOOL_ENTRIES.map((e) => (
            <SidebarLink key={e.to} to={e.to} label={e.label} active={location.pathname === e.to} onClose={onClose} />
          ))}
        </nav>
      </aside>
    </>
  );
}

function SidebarLink({
  to,
  label,
  active,
  onClose,
}: {
  to: string;
  label: string;
  active: boolean;
  onClose: () => void;
}) {
  return (
    <Link
      to={to}
      onClick={onClose}
      className={
        "rounded px-3 py-2 " +
        (active ? "bg-accent text-accent-foreground" : "hover:bg-accent/50")
      }
    >
      {label}
    </Link>
  );
}