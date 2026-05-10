"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import api from "@/lib/api";
import { ArrowLeft, Plus, Trash2, BarChart3, LineChart as LineIcon, PieChart as PieIcon, Hash, Table } from "lucide-react";
import Link from "next/link";

const WIDGET_TYPES = [
  { value: "line_chart", label: "Line Chart", icon: LineIcon },
  { value: "bar_chart", label: "Bar Chart", icon: BarChart3 },
  { value: "pie_chart", label: "Pie Chart", icon: PieIcon },
  { value: "kpi_card", label: "KPI Card", icon: Hash },
  { value: "table", label: "Table", icon: Table },
];

interface WidgetConfig {
  title: string;
  widget_type: string;
  query_config: { event_name: string; aggregation: string };
  time_range: string;
  position: { x: number; y: number; w: number; h: number };
}

export default function NewDashboardPage() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [isPublic, setIsPublic] = useState(false);
  const [widgets, setWidgets] = useState<WidgetConfig[]>([]);
  const [saving, setSaving] = useState(false);

  const addWidget = (type: string) => {
    setWidgets([
      ...widgets,
      {
        title: `Widget ${widgets.length + 1}`,
        widget_type: type,
        query_config: { event_name: "", aggregation: "count" },
        time_range: "7d",
        position: { x: (widgets.length % 2) * 6, y: Math.floor(widgets.length / 2) * 4, w: 6, h: 4 },
      },
    ]);
  };

  const removeWidget = (idx: number) => {
    setWidgets(widgets.filter((_, i) => i !== idx));
  };

  const updateWidget = (idx: number, field: string, value: any) => {
    const updated = [...widgets];
    if (field.startsWith("query_config.")) {
      const key = field.replace("query_config.", "");
      updated[idx] = { ...updated[idx], query_config: { ...updated[idx].query_config, [key]: value } };
    } else {
      (updated[idx] as any)[field] = value;
    }
    setWidgets(updated);
  };

  const handleSave = async () => {
    if (!name) return;
    setSaving(true);
    try {
      await api.post("/dashboards/", {
        name,
        description,
        is_public: isPublic,
        widgets,
      });
      router.push("/dashboard");
    } catch (err) {
      console.error(err);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div>
      <Link href="/dashboard" style={{ display: "inline-flex", alignItems: "center", gap: 8, color: "var(--text-secondary)", textDecoration: "none", fontSize: 13, marginBottom: 24 }}>
        <ArrowLeft size={16} /> Back to dashboards
      </Link>

      <h1 style={{ fontSize: 28, fontWeight: 700, marginBottom: 32 }}>Create Dashboard</h1>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 32 }}>
        {/* Config */}
        <div>
          <div className="glass-card" style={{ padding: 24, marginBottom: 20 }}>
            <h2 style={{ fontSize: 16, fontWeight: 600, marginBottom: 16 }}>Details</h2>
            <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
              <div>
                <label style={{ fontSize: 13, fontWeight: 500, color: "var(--text-secondary)", display: "block", marginBottom: 6 }}>Name *</label>
                <input className="input-field" placeholder="My Dashboard" value={name} onChange={(e) => setName(e.target.value)} />
              </div>
              <div>
                <label style={{ fontSize: 13, fontWeight: 500, color: "var(--text-secondary)", display: "block", marginBottom: 6 }}>Description</label>
                <input className="input-field" placeholder="Optional description" value={description} onChange={(e) => setDescription(e.target.value)} />
              </div>
              <label style={{ display: "flex", alignItems: "center", gap: 10, fontSize: 14, cursor: "pointer" }}>
                <input type="checkbox" checked={isPublic} onChange={(e) => setIsPublic(e.target.checked)} style={{ width: 16, height: 16, accentColor: "var(--accent-blue)" }} />
                Make dashboard public
              </label>
            </div>
          </div>

          {/* Add widget buttons */}
          <div className="glass-card" style={{ padding: 24 }}>
            <h2 style={{ fontSize: 16, fontWeight: 600, marginBottom: 16 }}>Add Widgets</h2>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 10 }}>
              {WIDGET_TYPES.map((wt) => (
                <button
                  key={wt.value}
                  className="btn-secondary"
                  onClick={() => addWidget(wt.value)}
                  style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 8, padding: "16px 12px" }}
                >
                  <wt.icon size={20} />
                  <span style={{ fontSize: 11 }}>{wt.label}</span>
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Widget list */}
        <div>
          <h2 style={{ fontSize: 16, fontWeight: 600, marginBottom: 16 }}>
            Widgets ({widgets.length})
          </h2>
          {widgets.length === 0 ? (
            <div className="glass-card" style={{ padding: 40, textAlign: "center" }}>
              <p style={{ color: "var(--text-muted)" }}>Click a widget type to add it</p>
            </div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              {widgets.map((w, idx) => (
                <div key={idx} className="glass-card" style={{ padding: 20 }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
                    <span className="badge badge-active">{w.widget_type.replace("_", " ")}</span>
                    <button onClick={() => removeWidget(idx)} style={{ background: "none", border: "none", cursor: "pointer", color: "var(--accent-rose)" }}>
                      <Trash2 size={16} />
                    </button>
                  </div>
                  <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                    <input className="input-field" placeholder="Widget title" value={w.title} onChange={(e) => updateWidget(idx, "title", e.target.value)} />
                    <input className="input-field" placeholder="Event name (e.g. page_view)" value={w.query_config.event_name} onChange={(e) => updateWidget(idx, "query_config.event_name", e.target.value)} />
                    <div style={{ display: "flex", gap: 10 }}>
                      <select className="input-field" value={w.query_config.aggregation} onChange={(e) => updateWidget(idx, "query_config.aggregation", e.target.value)}>
                        <option value="count">Count</option>
                        <option value="sum">Sum</option>
                        <option value="avg">Average</option>
                        <option value="unique">Unique</option>
                      </select>
                      <select className="input-field" value={w.time_range} onChange={(e) => updateWidget(idx, "time_range", e.target.value)}>
                        <option value="1h">1 hour</option>
                        <option value="24h">24 hours</option>
                        <option value="7d">7 days</option>
                        <option value="30d">30 days</option>
                      </select>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}

          {widgets.length > 0 && (
            <button
              className="btn-primary"
              onClick={handleSave}
              disabled={saving || !name}
              style={{ marginTop: 20, width: "100%", opacity: saving || !name ? 0.6 : 1 }}
            >
              {saving ? "Creating..." : "Create Dashboard"}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
