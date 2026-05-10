"use client";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import api from "@/lib/api";
import KPICard from "@/components/charts/KPICard";
import LineChartWidget from "@/components/charts/LineChartWidget";
import BarChartWidget from "@/components/charts/BarChartWidget";
import PieChartWidget from "@/components/charts/PieChartWidget";
import { Plus, LayoutGrid, RefreshCw, Users, Activity, Zap, AlertTriangle } from "lucide-react";
import Link from "next/link";

export default function DashboardPage() {
  const [timeRange, setTimeRange] = useState("7d");

  // Fetch dashboards
  const { data: dashboards, isLoading: dashLoading } = useQuery({
    queryKey: ["dashboards"],
    queryFn: () => api.get("/dashboards/").then((r) => r.data),
  });

  // Fetch event query for overview charts
  const { data: eventData, isLoading: eventsLoading } = useQuery({
    queryKey: ["events-overview", timeRange],
    queryFn: () =>
      api.get("/events/query", { params: { time_range: timeRange } }).then((r) => r.data),
  });

  // Fetch event names for pie chart
  const { data: eventNames } = useQuery({
    queryKey: ["event-names"],
    queryFn: () => api.get("/events/names").then((r) => r.data),
  });

  // Fetch alerts
  const { data: alerts } = useQuery({
    queryKey: ["alerts"],
    queryFn: () => api.get("/alerts/").then((r) => r.data),
  });

  const chartData = eventData?.labels?.map((label: string, i: number) => ({
    label,
    value: eventData.values[i],
  })) || [];

  const triggeredAlerts = alerts?.filter((a: any) => a.status === "triggered")?.length || 0;

  return (
    <div>
      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 32 }}>
        <div>
          <h1 style={{ fontSize: 28, fontWeight: 700, marginBottom: 4 }}>Dashboard</h1>
          <p style={{ color: "var(--text-secondary)", fontSize: 14 }}>
            Overview of your analytics platform
          </p>
        </div>
        <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
          <select
            className="input-field"
            value={timeRange}
            onChange={(e) => setTimeRange(e.target.value)}
            style={{ width: 120 }}
          >
            <option value="1h">Last hour</option>
            <option value="24h">Last 24h</option>
            <option value="7d">Last 7 days</option>
            <option value="30d">Last 30 days</option>
          </select>
          <Link href="/dashboard/new">
            <button className="btn-primary" style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <Plus size={16} /> New Dashboard
            </button>
          </Link>
        </div>
      </div>

      {/* KPI Row */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 20, marginBottom: 28 }}>
        <KPICard
          title="Total Events"
          value={eventData?.total || 0}
          change={12.5}
          subtitle="vs. previous period"
          icon={<Activity size={18} />}
        />
        <KPICard
          title="Active Dashboards"
          value={dashboards?.length || 0}
          icon={<LayoutGrid size={18} />}
        />
        <KPICard
          title="Event Types"
          value={eventNames?.length || 0}
          icon={<Zap size={18} />}
        />
        <KPICard
          title="Triggered Alerts"
          value={triggeredAlerts}
          change={triggeredAlerts > 0 ? triggeredAlerts * 10 : 0}
          subtitle={triggeredAlerts > 0 ? "needs attention" : "all clear"}
          icon={<AlertTriangle size={18} />}
        />
      </div>

      {/* Charts Row */}
      <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr", gap: 20, marginBottom: 28 }}>
        <div style={{ minHeight: 320 }}>
          {eventsLoading ? (
            <div className="skeleton" style={{ height: 320 }} />
          ) : (
            <LineChartWidget data={chartData} title="Events Over Time" color="#6366f1" />
          )}
        </div>
        <div style={{ minHeight: 320 }}>
          <BarChartWidget data={chartData.slice(-7)} title="Daily Breakdown" color="#8b5cf6" />
        </div>
      </div>

      {/* Dashboards List */}
      <div style={{ marginBottom: 28 }}>
        <h2 style={{ fontSize: 18, fontWeight: 600, marginBottom: 16, display: "flex", alignItems: "center", gap: 8 }}>
          <LayoutGrid size={20} /> Your Dashboards
        </h2>
        {dashLoading ? (
          <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 16 }}>
            {[1, 2, 3].map((i) => (
              <div key={i} className="skeleton" style={{ height: 120 }} />
            ))}
          </div>
        ) : dashboards?.length > 0 ? (
          <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 16 }}>
            {dashboards.map((d: any) => (
              <Link key={d.id} href={`/dashboard/${d.id}`} style={{ textDecoration: "none", color: "inherit" }}>
                <div className="glass-card" style={{ padding: 20, cursor: "pointer" }}>
                  <h3 style={{ fontSize: 15, fontWeight: 600, marginBottom: 6 }}>{d.name}</h3>
                  <p style={{ fontSize: 12, color: "var(--text-muted)", marginBottom: 12 }}>
                    {d.description || "No description"}
                  </p>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <span style={{ fontSize: 11, color: "var(--text-muted)" }}>
                      {d.widgets?.length || 0} widgets
                    </span>
                    {d.is_public && (
                      <span className="badge badge-active" style={{ fontSize: 10 }}>Public</span>
                    )}
                  </div>
                </div>
              </Link>
            ))}
          </div>
        ) : (
          <div className="glass-card" style={{ padding: 40, textAlign: "center" }}>
            <LayoutGrid size={40} style={{ color: "var(--text-muted)", margin: "0 auto 12px" }} />
            <p style={{ color: "var(--text-secondary)", marginBottom: 16 }}>No dashboards yet</p>
            <Link href="/dashboard/new">
              <button className="btn-primary">Create your first dashboard</button>
            </Link>
          </div>
        )}
      </div>
    </div>
  );
}
