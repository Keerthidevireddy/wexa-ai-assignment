"use client";
import { TrendingUp, TrendingDown, Minus } from "lucide-react";

interface Props {
  title: string;
  value: string | number;
  change?: number; // percentage change
  subtitle?: string;
  icon?: React.ReactNode;
}

export default function KPICard({ title, value, change, subtitle, icon }: Props) {
  const trend = change && change > 0 ? "up" : change && change < 0 ? "down" : "neutral";

  return (
    <div className="glass-card" style={{ padding: 24, height: "100%", display: "flex", flexDirection: "column", justifyContent: "space-between" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
        <span style={{ fontSize: 13, fontWeight: 500, color: "var(--text-secondary)", textTransform: "uppercase", letterSpacing: "0.05em" }}>
          {title}
        </span>
        {icon && (
          <div style={{
            width: 36, height: 36, borderRadius: 10,
            background: "rgba(99, 102, 241, 0.1)",
            display: "flex", alignItems: "center", justifyContent: "center",
            color: "var(--accent-blue)"
          }}>
            {icon}
          </div>
        )}
      </div>
      <div className="kpi-value" style={{ marginTop: 12 }}>
        {typeof value === "number" ? value.toLocaleString() : value}
      </div>
      {(change !== undefined || subtitle) && (
        <div style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 12 }}>
          {change !== undefined && (
            <span
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: 4,
                fontSize: 12,
                fontWeight: 600,
                padding: "3px 8px",
                borderRadius: 6,
                background: trend === "up"
                  ? "rgba(16, 185, 129, 0.12)"
                  : trend === "down"
                  ? "rgba(244, 63, 94, 0.12)"
                  : "rgba(136, 136, 160, 0.12)",
                color: trend === "up"
                  ? "var(--accent-emerald)"
                  : trend === "down"
                  ? "var(--accent-rose)"
                  : "var(--text-secondary)",
              }}
            >
              {trend === "up" ? <TrendingUp size={12} /> : trend === "down" ? <TrendingDown size={12} /> : <Minus size={12} />}
              {Math.abs(change).toFixed(1)}%
            </span>
          )}
          {subtitle && (
            <span style={{ fontSize: 12, color: "var(--text-muted)" }}>
              {subtitle}
            </span>
          )}
        </div>
      )}
    </div>
  );
}
