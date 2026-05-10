"use client";
import { useQuery } from "@tanstack/react-query";
import { useParams } from "next/navigation";
import api from "@/lib/api";
import LineChartWidget from "@/components/charts/LineChartWidget";
import BarChartWidget from "@/components/charts/BarChartWidget";
import PieChartWidget from "@/components/charts/PieChartWidget";
import KPICard from "@/components/charts/KPICard";
import { ArrowLeft, Share2, Maximize, RefreshCw } from "lucide-react";
import Link from "next/link";
import { useState, useEffect } from "react";

export default function DashboardDetailPage() {
  const params = useParams();
  const dashboardId = params.id as string;
  const [autoRefresh, setAutoRefresh] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);

  // Fullscreen presentation mode
  const toggleFullscreen = () => {
    if (!document.fullscreenElement) {
      document.documentElement.requestFullscreen();
      setIsFullscreen(true);
    } else {
      document.exitFullscreen();
      setIsFullscreen(false);
    }
  };

  useEffect(() => {
    const onFullscreenChange = () => setIsFullscreen(!!document.fullscreenElement);
    document.addEventListener("fullscreenchange", onFullscreenChange);
    return () => document.removeEventListener("fullscreenchange", onFullscreenChange);
  }, []);

  const { data: dashboard, isLoading } = useQuery({
    queryKey: ["dashboard", dashboardId],
    queryFn: () => api.get(`/dashboards/${dashboardId}`).then((r) => r.data),
  });

  // Fetch widget data for each widget
  const { data: widgetDataMap, refetch } = useQuery({
    queryKey: ["widget-data", dashboardId],
    queryFn: async () => {
      if (!dashboard?.widgets) return {};
      const results: Record<string, any> = {};
      for (const widget of dashboard.widgets) {
        try {
          const res = await api.get("/events/query", {
            params: {
              event_name: widget.query_config?.event_name || undefined,
              time_range: widget.time_range,
              aggregation: widget.query_config?.aggregation || "count",
            },
          });
          results[widget.id] = res.data;
        } catch {
          results[widget.id] = { labels: [], values: [], total: 0 };
        }
      }
      return results;
    },
    enabled: !!dashboard?.widgets,
  });

  // Auto refresh
  useEffect(() => {
    if (!autoRefresh || !dashboard?.refresh_interval) return;
    const interval = setInterval(() => refetch(), (dashboard.refresh_interval || 30) * 1000);
    return () => clearInterval(interval);
  }, [autoRefresh, dashboard, refetch]);

  const renderWidget = (widget: any) => {
    const data = widgetDataMap?.[widget.id];
    const chartData = data?.labels?.map((label: string, i: number) => ({
      label,
      value: data.values[i],
    })) || [];

    switch (widget.widget_type) {
      case "line_chart":
        return <LineChartWidget data={chartData} title={widget.title} />;
      case "bar_chart":
        return <BarChartWidget data={chartData} title={widget.title} />;
      case "pie_chart":
        return <PieChartWidget data={chartData} title={widget.title} />;
      case "kpi_card":
        return <KPICard title={widget.title} value={data?.total || 0} change={8.5} subtitle="vs. previous" />;
      case "table":
        return (
          <div className="glass-card" style={{ padding: 20, height: "100%" }}>
            <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 12, color: "var(--text-secondary)" }}>{widget.title}</h3>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
              <thead>
                <tr style={{ borderBottom: "1px solid var(--border-color)" }}>
                  <th style={{ padding: "8px 0", textAlign: "left", color: "var(--text-muted)" }}>Period</th>
                  <th style={{ padding: "8px 0", textAlign: "right", color: "var(--text-muted)" }}>Value</th>
                </tr>
              </thead>
              <tbody>
                {chartData.map((row: any, i: number) => (
                  <tr key={i} style={{ borderBottom: "1px solid var(--border-color)" }}>
                    <td style={{ padding: "8px 0", color: "var(--text-secondary)" }}>{row.label}</td>
                    <td style={{ padding: "8px 0", textAlign: "right", fontWeight: 500 }}>{row.value}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        );
      default:
        return <div className="glass-card" style={{ padding: 20 }}>Unknown widget type</div>;
    }
  };

  if (isLoading) {
    return (
      <div>
        <div className="skeleton" style={{ height: 40, width: 300, marginBottom: 32 }} />
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}>
          {[1, 2, 3, 4].map((i) => <div key={i} className="skeleton" style={{ height: 280 }} />)}
        </div>
      </div>
    );
  }

  if (!dashboard) {
    return (
      <div style={{ textAlign: "center", padding: 60 }}>
        <p style={{ color: "var(--text-muted)" }}>Dashboard not found</p>
        <Link href="/dashboard"><button className="btn-secondary" style={{ marginTop: 16 }}>Back</button></Link>
      </div>
    );
  }

  return (
    <div style={isFullscreen ? { padding: 40, background: "var(--bg-primary)", minHeight: "100vh" } : {}}>
      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 28 }}>
        <div>
          <Link href="/dashboard" style={{ display: "inline-flex", alignItems: "center", gap: 6, color: "var(--text-muted)", textDecoration: "none", fontSize: 12, marginBottom: 12 }}>
            <ArrowLeft size={14} /> Back
          </Link>
          <h1 style={{ fontSize: 24, fontWeight: 700, marginBottom: 4 }}>{dashboard.name}</h1>
          <p style={{ fontSize: 13, color: "var(--text-secondary)" }}>{dashboard.description || "No description"}</p>
        </div>
        <div style={{ display: "flex", gap: 10 }}>
          <button
            className={autoRefresh ? "btn-primary" : "btn-secondary"}
            onClick={() => setAutoRefresh(!autoRefresh)}
            style={{ display: "flex", alignItems: "center", gap: 6, padding: "8px 14px", fontSize: 12 }}
          >
            <RefreshCw size={14} className={autoRefresh ? "animate-spin" : ""} />
            {autoRefresh ? "Auto-refreshing" : "Auto-refresh"}
          </button>
          {dashboard.is_public && dashboard.public_slug && (
            <button
              className="btn-secondary"
              onClick={() => navigator.clipboard.writeText(`${window.location.origin}/dashboard/public/${dashboard.public_slug}`)}
              style={{ display: "flex", alignItems: "center", gap: 6, padding: "8px 14px", fontSize: 12 }}
            >
              <Share2 size={14} /> Share
            </button>
          )}
          <button
            className={isFullscreen ? "btn-primary" : "btn-secondary"}
            onClick={toggleFullscreen}
            style={{ display: "flex", alignItems: "center", gap: 6, padding: "8px 14px", fontSize: 12 }}
          >
            <Maximize size={14} />
            {isFullscreen ? "Exit Fullscreen" : "Present"}
          </button>
        </div>
      </div>

      {/* Widgets grid */}
      {dashboard.widgets?.length > 0 ? (
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(12, 1fr)",
            gap: 20,
            gridAutoRows: "minmax(80px, auto)",
          }}
        >
          {dashboard.widgets.map((widget: any) => {
            const pos = widget.position || { x: 0, y: 0, w: 6, h: 4 };
            return (
              <div
                key={widget.id}
                style={{
                  gridColumn: `span ${pos.w}`,
                  minHeight: pos.h * 80,
                }}
              >
                {renderWidget(widget)}
              </div>
            );
          })}
        </div>
      ) : (
        <div className="glass-card" style={{ padding: 48, textAlign: "center" }}>
          <p style={{ color: "var(--text-muted)" }}>No widgets yet. Edit this dashboard to add widgets.</p>
        </div>
      )}
    </div>
  );
}
