"use client";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import api from "@/lib/api";
import { Bell, Plus, Trash2, VolumeX, Clock, AlertTriangle, CheckCircle2, XCircle } from "lucide-react";

const STATUS_CONFIG: Record<string, { badge: string; icon: typeof Bell; color: string }> = {
  active: { badge: "badge-active", icon: CheckCircle2, color: "var(--accent-emerald)" },
  triggered: { badge: "badge-triggered", icon: AlertTriangle, color: "var(--accent-rose)" },
  resolved: { badge: "badge-resolved", icon: CheckCircle2, color: "var(--accent-blue)" },
  muted: { badge: "badge-muted", icon: VolumeX, color: "var(--accent-amber)" },
};

export default function AlertsPage() {
  const queryClient = useQueryClient();
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({
    name: "",
    description: "",
    event_name: "",
    metric: "count",
    operator: ">",
    threshold: 100,
    window_minutes: 10,
    channels: { in_app: true, email: false, webhook: null as string | null },
  });

  const { data: alerts, isLoading } = useQuery({
    queryKey: ["alerts"],
    queryFn: () => api.get("/alerts/").then((r) => r.data),
  });

  const createMutation = useMutation({
    mutationFn: (data: typeof form) => api.post("/alerts/", data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["alerts"] });
      setShowCreate(false);
      setForm({ name: "", description: "", event_name: "", metric: "count", operator: ">", threshold: 100, window_minutes: 10, channels: { in_app: true, email: false, webhook: null } });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.delete(`/alerts/${id}`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["alerts"] }),
  });

  const muteMutation = useMutation({
    mutationFn: ({ id, minutes }: { id: string; minutes: number }) =>
      api.post(`/alerts/${id}/mute`, { minutes }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["alerts"] }),
  });

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 32 }}>
        <div>
          <h1 style={{ fontSize: 28, fontWeight: 700, marginBottom: 4 }}>Alerts</h1>
          <p style={{ color: "var(--text-secondary)", fontSize: 14 }}>
            Set threshold-based alerts on your metrics
          </p>
        </div>
        <button className="btn-primary" onClick={() => setShowCreate(!showCreate)} style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <Plus size={16} /> New Alert
        </button>
      </div>

      {/* Create Alert Form */}
      {showCreate && (
        <div className="glass-card" style={{ padding: 28, marginBottom: 28, maxWidth: 600 }}>
          <h2 style={{ fontSize: 16, fontWeight: 600, marginBottom: 20 }}>Create Alert Rule</h2>
          <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }}>
              <div>
                <label style={{ fontSize: 13, fontWeight: 500, color: "var(--text-secondary)", display: "block", marginBottom: 6 }}>Alert Name *</label>
                <input className="input-field" placeholder="High error rate" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
              </div>
              <div>
                <label style={{ fontSize: 13, fontWeight: 500, color: "var(--text-secondary)", display: "block", marginBottom: 6 }}>Event Name *</label>
                <input className="input-field" placeholder="error" value={form.event_name} onChange={(e) => setForm({ ...form, event_name: e.target.value })} />
              </div>
            </div>
            <div>
              <label style={{ fontSize: 13, fontWeight: 500, color: "var(--text-secondary)", display: "block", marginBottom: 6 }}>Description</label>
              <input className="input-field" placeholder="Optional description" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
            </div>
            <div style={{ display: "flex", gap: 12, alignItems: "end" }}>
              <div style={{ flex: 1 }}>
                <label style={{ fontSize: 13, fontWeight: 500, color: "var(--text-secondary)", display: "block", marginBottom: 6 }}>When</label>
                <select className="input-field" value={form.metric} onChange={(e) => setForm({ ...form, metric: e.target.value })}>
                  <option value="count">Count</option>
                  <option value="sum">Sum</option>
                  <option value="avg">Average</option>
                  <option value="unique">Unique Users</option>
                </select>
              </div>
              <div style={{ flex: 0.6 }}>
                <label style={{ fontSize: 13, fontWeight: 500, color: "var(--text-secondary)", display: "block", marginBottom: 6 }}>Operator</label>
                <select className="input-field" value={form.operator} onChange={(e) => setForm({ ...form, operator: e.target.value })}>
                  <option value=">">&gt;</option>
                  <option value="<">&lt;</option>
                  <option value=">=">&gt;=</option>
                  <option value="<=">&lt;=</option>
                  <option value="==">==</option>
                </select>
              </div>
              <div style={{ flex: 1 }}>
                <label style={{ fontSize: 13, fontWeight: 500, color: "var(--text-secondary)", display: "block", marginBottom: 6 }}>Threshold</label>
                <input className="input-field" type="number" value={form.threshold} onChange={(e) => setForm({ ...form, threshold: Number(e.target.value) })} />
              </div>
              <div style={{ flex: 1 }}>
                <label style={{ fontSize: 13, fontWeight: 500, color: "var(--text-secondary)", display: "block", marginBottom: 6 }}>Window (min)</label>
                <input className="input-field" type="number" value={form.window_minutes} min={1} onChange={(e) => setForm({ ...form, window_minutes: Number(e.target.value) })} />
              </div>
            </div>

            {/* Channels */}
            <div>
              <label style={{ fontSize: 13, fontWeight: 500, color: "var(--text-secondary)", display: "block", marginBottom: 8 }}>Notification Channels</label>
              <div style={{ display: "flex", gap: 16 }}>
                <label style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13, cursor: "pointer" }}>
                  <input type="checkbox" checked={form.channels.in_app} onChange={(e) => setForm({ ...form, channels: { ...form.channels, in_app: e.target.checked } })} style={{ accentColor: "var(--accent-blue)" }} />
                  In-app
                </label>
                <label style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13, cursor: "pointer" }}>
                  <input type="checkbox" checked={form.channels.email} onChange={(e) => setForm({ ...form, channels: { ...form.channels, email: e.target.checked } })} style={{ accentColor: "var(--accent-blue)" }} />
                  Email
                </label>
              </div>
            </div>

            <div style={{ display: "flex", gap: 10, marginTop: 8 }}>
              <button className="btn-primary" onClick={() => createMutation.mutate(form)} disabled={!form.name || !form.event_name || createMutation.isPending}>
                {createMutation.isPending ? "Creating..." : "Create Alert"}
              </button>
              <button className="btn-secondary" onClick={() => setShowCreate(false)}>Cancel</button>
            </div>
          </div>
        </div>
      )}

      {/* Alerts List */}
      {isLoading ? (
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {[1, 2, 3].map((i) => <div key={i} className="skeleton" style={{ height: 100 }} />)}
        </div>
      ) : alerts?.length > 0 ? (
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {alerts.map((alert: any) => {
            const config = STATUS_CONFIG[alert.status] || STATUS_CONFIG.active;
            const Icon = config.icon;
            return (
              <div key={alert.id} className="glass-card" style={{ padding: 20 }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                  <div style={{ display: "flex", gap: 14, alignItems: "flex-start" }}>
                    <div style={{ width: 40, height: 40, borderRadius: 10, background: `${config.color}15`, display: "flex", alignItems: "center", justifyContent: "center", color: config.color, flexShrink: 0, marginTop: 2 }}>
                      <Icon size={18} />
                    </div>
                    <div>
                      <h3 style={{ fontSize: 15, fontWeight: 600, marginBottom: 4 }}>{alert.name}</h3>
                      <p style={{ fontSize: 12, color: "var(--text-muted)", marginBottom: 8 }}>
                        {alert.description || `When ${alert.event_name} ${alert.metric} ${alert.operator} ${alert.threshold} for ${alert.window_minutes}min`}
                      </p>
                      <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                        <span className={`badge ${config.badge}`}>{alert.status}</span>
                        <span style={{ fontSize: 11, color: "var(--text-muted)" }}>
                          <Clock size={10} style={{ display: "inline", marginRight: 4 }} />
                          {new Date(alert.created_at).toLocaleDateString()}
                        </span>
                        {alert.last_triggered_at && (
                          <span style={{ fontSize: 11, color: "var(--accent-rose)" }}>
                            Last triggered: {new Date(alert.last_triggered_at).toLocaleString()}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                  <div style={{ display: "flex", gap: 8 }}>
                    {alert.status !== "muted" && (
                      <button
                        className="btn-secondary"
                        onClick={() => muteMutation.mutate({ id: alert.id, minutes: 60 })}
                        style={{ padding: "6px 12px", fontSize: 12 }}
                        title="Mute for 1 hour"
                      >
                        <VolumeX size={14} />
                      </button>
                    )}
                    <button
                      onClick={() => { if (confirm("Delete this alert?")) deleteMutation.mutate(alert.id); }}
                      style={{ background: "none", border: "none", cursor: "pointer", color: "var(--text-muted)", padding: 6 }}
                    >
                      <Trash2 size={16} />
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        <div className="glass-card" style={{ padding: 48, textAlign: "center" }}>
          <Bell size={40} style={{ color: "var(--text-muted)", margin: "0 auto 12px" }} />
          <p style={{ color: "var(--text-secondary)", marginBottom: 16 }}>No alerts configured</p>
          <button className="btn-primary" onClick={() => setShowCreate(true)}>Create your first alert</button>
        </div>
      )}
    </div>
  );
}
