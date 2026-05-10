"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard, Activity, Bell, Database, Settings, LogOut, ChevronLeft,
  ChevronRight, Zap,
} from "lucide-react";
import { useAuthStore } from "@/store/auth";
import { useState } from "react";

const navItems = [
  { href: "/dashboard", label: "Dashboards", icon: LayoutDashboard },
  { href: "/events", label: "Events", icon: Database },
  { href: "/alerts", label: "Alerts", icon: Bell },
  { href: "/live", label: "Live Stream", icon: Activity },
  { href: "/settings", label: "Settings", icon: Settings },
];

export default function Sidebar() {
  const pathname = usePathname();
  const { user, logout } = useAuthStore();
  const [collapsed, setCollapsed] = useState(false);

  return (
    <aside
      style={{
        width: collapsed ? 72 : 260,
        minHeight: "100vh",
        background: "var(--bg-secondary)",
        borderRight: "1px solid var(--border-color)",
        display: "flex",
        flexDirection: "column",
        padding: collapsed ? "20px 8px" : "20px 16px",
        transition: "all 0.3s cubic-bezier(0.4, 0, 0.2, 1)",
        position: "relative",
      }}
    >
      {/* Logo */}
      <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 40, padding: "0 4px" }}>
        <div
          style={{
            width: 36,
            height: 36,
            borderRadius: 10,
            background: "var(--gradient-primary)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            flexShrink: 0,
          }}
        >
          <Zap size={18} color="white" />
        </div>
        {!collapsed && (
          <span style={{ fontWeight: 700, fontSize: 18, letterSpacing: "-0.02em" }}>
            Analytics
          </span>
        )}
      </div>

      {/* Collapse toggle */}
      <button
        onClick={() => setCollapsed(!collapsed)}
        style={{
          position: "absolute",
          right: -14,
          top: 40,
          width: 28,
          height: 28,
          borderRadius: "50%",
          background: "var(--bg-card)",
          border: "1px solid var(--border-color)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          cursor: "pointer",
          color: "var(--text-secondary)",
          zIndex: 10,
        }}
      >
        {collapsed ? <ChevronRight size={14} /> : <ChevronLeft size={14} />}
      </button>

      {/* Nav */}
      <nav style={{ flex: 1, display: "flex", flexDirection: "column", gap: 4 }}>
        {navItems.map((item) => {
          const active = pathname.startsWith(item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`sidebar-link ${active ? "active" : ""}`}
              style={{
                justifyContent: collapsed ? "center" : "flex-start",
                padding: collapsed ? "12px" : undefined,
              }}
              title={collapsed ? item.label : undefined}
            >
              <item.icon size={20} />
              {!collapsed && item.label}
            </Link>
          );
        })}
      </nav>

      {/* User info */}
      <div
        style={{
          borderTop: "1px solid var(--border-color)",
          paddingTop: 16,
          display: "flex",
          alignItems: "center",
          gap: 12,
        }}
      >
        <div
          style={{
            width: 36,
            height: 36,
            borderRadius: "50%",
            background: "var(--gradient-primary)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            flexShrink: 0,
            fontSize: 14,
            fontWeight: 700,
          }}
        >
          {user?.full_name?.[0]?.toUpperCase() || "U"}
        </div>
        {!collapsed && (
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ fontSize: 13, fontWeight: 600, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
              {user?.full_name || "User"}
            </div>
            <div style={{ fontSize: 11, color: "var(--text-muted)" }}>
              {user?.role}
            </div>
          </div>
        )}
        <button
          onClick={logout}
          style={{
            background: "none",
            border: "none",
            cursor: "pointer",
            color: "var(--text-muted)",
            padding: 4,
          }}
          title="Logout"
        >
          <LogOut size={16} />
        </button>
      </div>
    </aside>
  );
}
