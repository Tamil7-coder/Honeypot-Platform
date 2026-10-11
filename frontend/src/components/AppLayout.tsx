import { useState } from "react";
import { NavLink, Outlet } from "react-router-dom";
import { motion } from "framer-motion";
import { LayoutDashboard, ShieldAlert, BarChart3, FileBarChart, Settings, ChevronsLeft, ChevronsRight, Radar, LogOut } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import NotificationBell from "./NotificationBell";
import LiveStatusIndicator from "./LiveStatusIndicator";
import ThemeToggle from "./ThemeToggle";

const NAV_ITEMS = [
  { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { to: "/attacks", label: "Attack Monitor", icon: ShieldAlert },
  { to: "/analytics", label: "Attack Analytics", icon: BarChart3 },
  { to: "/reports", label: "Reports", icon: FileBarChart },
  { to: "/settings", label: "Settings", icon: Settings },
];

export default function AppLayout() {
  const { user, logout } = useAuth();
  const [collapsed, setCollapsed] = useState(false);

  return (
    <div className="flex h-screen bg-transparent text-slate-200">
      <motion.aside
        animate={{ width: collapsed ? 76 : 240 }}
        transition={{ duration: 0.2, ease: "easeInOut" }}
        className="shrink-0 border-r border-soc-panelBorder glass-panel flex flex-col overflow-hidden"
      >
        <div className="flex items-center gap-2 px-5 py-5 border-b border-soc-panelBorder">
          <div className="relative shrink-0">
            <div className="absolute inset-0 animate-spin-slow rounded-full bg-signature-gradient opacity-30 blur-sm" />
            <div className="relative rounded-full bg-soc-bgElevated p-1.5 ring-1 ring-soc-panelBorder">
              <Radar size={16} className="text-soc-cyan" />
            </div>
          </div>
          {!collapsed && (
            <div className="min-w-0">
              <h1 className="text-slate-100 text-sm tracking-widest font-semibold truncate">HONEYNET SOC</h1>
              <p className="text-[10px] text-soc-textFaint truncate">Attack Analytics Platform</p>
            </div>
          )}
        </div>

        <nav className="flex-1 py-4">
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              title={item.label}
              className={({ isActive }) =>
                `flex items-center gap-3 px-5 py-2.5 text-sm transition-colors border-l-2 ${
                  isActive
                    ? "border-soc-cyan text-soc-cyan bg-white/5"
                    : "border-transparent text-soc-textMuted hover:text-slate-100 hover:bg-white/5"
                }`
              }
            >
              <item.icon size={17} strokeWidth={2} className="shrink-0" />
              {!collapsed && <span className="truncate">{item.label}</span>}
            </NavLink>
          ))}
        </nav>

        <button
          onClick={() => setCollapsed((v) => !v)}
          className="flex items-center gap-2 px-5 py-3 text-xs text-soc-textFaint hover:text-slate-200 hover:bg-white/5 border-t border-soc-panelBorder transition-colors"
        >
          {collapsed ? <ChevronsRight size={15} /> : <ChevronsLeft size={15} />}
          {!collapsed && "Collapse"}
        </button>

        <div className="px-5 py-4 border-t border-soc-panelBorder text-xs">
          {!collapsed ? (
            <>
              <p className="text-slate-300 truncate">{user?.username}</p>
              <p className="text-soc-textMuted uppercase tracking-wide">{user?.role}</p>
              <button
                onClick={logout}
                className="mt-3 flex items-center gap-1.5 text-soc-danger hover:underline text-xs"
              >
                <LogOut size={12} /> Sign out
              </button>
            </>
          ) : (
            <button onClick={logout} title="Sign out" className="text-soc-danger">
              <LogOut size={16} />
            </button>
          )}
        </div>
      </motion.aside>

      <div className="flex flex-1 flex-col overflow-hidden">
        <header className="flex items-center justify-end gap-3 border-b border-soc-panelBorder glass-panel px-6 py-3">
          <LiveStatusIndicator />
          <ThemeToggle />
          <NotificationBell />
        </header>
        <main className="flex-1 overflow-y-auto">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
