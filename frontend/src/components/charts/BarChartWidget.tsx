"use client";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from "recharts";

interface Props {
  data: { label: string; value: number }[];
  color?: string;
  title?: string;
}

export default function BarChartWidget({ data, color = "#8b5cf6", title }: Props) {
  return (
    <div className="glass-card" style={{ padding: 20, height: "100%" }}>
      {title && (
        <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 16, color: "var(--text-secondary)" }}>
          {title}
        </h3>
      )}
      <ResponsiveContainer width="100%" height="100%" minHeight={200}>
        <BarChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(0,0,0,0.06)" />
          <XAxis
            dataKey="label"
            stroke="var(--text-muted)"
            fontSize={11}
            tickLine={false}
            axisLine={false}
          />
          <YAxis
            stroke="var(--text-muted)"
            fontSize={11}
            tickLine={false}
            axisLine={false}
          />
          <Tooltip
            contentStyle={{
              background: "var(--bg-card)",
              border: "1px solid var(--border-color)",
              borderRadius: 10,
              fontSize: 12,
              boxShadow: "0 8px 24px rgba(0,0,0,0.08)",
            }}
          />
          <Bar
            dataKey="value"
            fill={color}
            radius={[6, 6, 0, 0]}
            maxBarSize={40}
          />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
