"use client";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useState, useRef } from "react";
import api from "@/lib/api";
import { Database, Upload, Send, Clock, Tag } from "lucide-react";

export default function EventsPage() {
  const queryClient = useQueryClient();
  const [tab, setTab] = useState<"recent" | "ingest" | "csv">("recent");
  const [eventName, setEventName] = useState("");
  const [eventProps, setEventProps] = useState("{}");
  const fileRef = useRef<HTMLInputElement>(null);

  const { data: recentEvents, isLoading } = useQuery({
    queryKey: ["recent-events"],
    queryFn: () => api.get("/events/recent?limit=50").then((r) => r.data),
  });

  const { data: eventNames } = useQuery({
    queryKey: ["event-names"],
    queryFn: () => api.get("/events/names").then((r) => r.data),
  });

  const ingestMutation = useMutation({
    mutationFn: (data: { name: string; properties: Record<string, unknown> }) =>
      api.post("/events/ingest", data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["recent-events"] });
      queryClient.invalidateQueries({ queryKey: ["event-names"] });
      setEventName("");
      setEventProps("{}");
    },
  });

  const csvMutation = useMutation({
    mutationFn: (file: File) => {
      const form = new FormData();
      form.append("file", file);
      return api.post("/events/ingest/csv", form, {
        headers: { "Content-Type": "multipart/form-data" },
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["recent-events"] });
    },
  });

  const handleIngest = () => {
    try {
      const props = JSON.parse(eventProps);
      ingestMutation.mutate({ name: eventName, properties: props });
    } catch {
      alert("Invalid JSON in properties");
    }
  };

  const tabs = [
    { key: "recent", label: "Recent Events", icon: Clock },
    { key: "ingest", label: "Ingest Event", icon: Send },
    { key: "csv", label: "CSV Upload", icon: Upload },
  ] as const;

  return (
    <div>
      <h1 style={{ fontSize: 28, fontWeight: 700, marginBottom: 8 }}>Events</h1>
      <p style={{ color: "var(--text-secondary)", fontSize: 14, marginBottom: 28 }}>
        Ingest and explore your event data
      </p>

      {/* Event name pills */}
      {eventNames && eventNames.length > 0 && (
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 24 }}>
          {eventNames.map((name: string) => (
            <span key={name} className="badge badge-active" style={{ cursor: "pointer" }}>
              <Tag size={10} /> {name}
            </span>
          ))}
        </div>
      )}

      {/* Tabs */}
      <div style={{ display: "flex", gap: 4, marginBottom: 24, background: "var(--bg-secondary)", borderRadius: 12, padding: 4, width: "fit-content" }}>
        {tabs.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            style={{
              display: "flex", alignItems: "center", gap: 8,
              padding: "8px 16px", borderRadius: 8, border: "none",
              background: tab === t.key ? "var(--bg-card)" : "transparent",
              color: tab === t.key ? "var(--text-primary)" : "var(--text-muted)",
              cursor: "pointer", fontSize: 13, fontWeight: 500,
              transition: "all 0.2s ease",
            }}
          >
            <t.icon size={14} /> {t.label}
          </button>
        ))}
      </div>

      {/* Recent Events */}
      {tab === "recent" && (
        <div className="glass-card" style={{ overflow: "hidden" }}>
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse" }}>
              <thead>
                <tr style={{ borderBottom: "1px solid var(--border-color)" }}>
                  {["Event Name", "Source", "User ID", "Properties", "Timestamp"].map((h) => (
                    <th key={h} style={{ padding: "14px 16px", textAlign: "left", fontSize: 12, fontWeight: 600, color: "var(--text-secondary)", textTransform: "uppercase", letterSpacing: "0.04em" }}>
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {isLoading ? (
                  [...Array(5)].map((_, i) => (
                    <tr key={i}>
                      <td colSpan={5} style={{ padding: 16 }}><div className="skeleton" style={{ height: 20 }} /></td>
                    </tr>
                  ))
                ) : recentEvents?.length > 0 ? (
                  recentEvents.map((e: any) => (
                    <tr key={e.id} style={{ borderBottom: "1px solid var(--border-color)" }}>
                      <td style={{ padding: "12px 16px", fontSize: 13, fontWeight: 500 }}>{e.name}</td>
                      <td style={{ padding: "12px 16px" }}>
                        <span className="badge badge-active" style={{ fontSize: 10 }}>{e.source}</span>
                      </td>
                      <td style={{ padding: "12px 16px", fontSize: 12, color: "var(--text-muted)", fontFamily: "monospace" }}>{e.user_id || "—"}</td>
                      <td style={{ padding: "12px 16px", fontSize: 11, color: "var(--text-muted)", fontFamily: "monospace", maxWidth: 200, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                        {JSON.stringify(e.properties)}
                      </td>
                      <td style={{ padding: "12px 16px", fontSize: 12, color: "var(--text-muted)" }}>
                        {new Date(e.created_at).toLocaleString()}
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={5} style={{ padding: 40, textAlign: "center", color: "var(--text-muted)" }}>
                      No events yet. Start ingesting data!
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Ingest Event */}
      {tab === "ingest" && (
        <div className="glass-card" style={{ padding: 28, maxWidth: 500 }}>
          <h2 style={{ fontSize: 16, fontWeight: 600, marginBottom: 20 }}>Send Event</h2>
          <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            <div>
              <label style={{ fontSize: 13, fontWeight: 500, color: "var(--text-secondary)", display: "block", marginBottom: 6 }}>Event Name *</label>
              <input className="input-field" placeholder="page_view" value={eventName} onChange={(e) => setEventName(e.target.value)} />
            </div>
            <div>
              <label style={{ fontSize: 13, fontWeight: 500, color: "var(--text-secondary)", display: "block", marginBottom: 6 }}>Properties (JSON)</label>
              <textarea
                className="input-field"
                placeholder='{"page": "/home", "browser": "chrome"}'
                value={eventProps}
                onChange={(e) => setEventProps(e.target.value)}
                rows={4}
                style={{ resize: "vertical", fontFamily: "monospace", fontSize: 12 }}
              />
            </div>
            <button className="btn-primary" onClick={handleIngest} disabled={!eventName || ingestMutation.isPending}>
              {ingestMutation.isPending ? "Sending..." : "Send Event"}
            </button>
            {ingestMutation.isSuccess && (
              <p style={{ fontSize: 13, color: "var(--accent-emerald)" }}>✓ Event ingested successfully!</p>
            )}
          </div>
        </div>
      )}

      {/* CSV Upload */}
      {tab === "csv" && (
        <div className="glass-card" style={{ padding: 28, maxWidth: 500 }}>
          <h2 style={{ fontSize: 16, fontWeight: 600, marginBottom: 20 }}>Upload CSV</h2>
          <p style={{ fontSize: 13, color: "var(--text-secondary)", marginBottom: 16 }}>
            CSV must have a &quot;name&quot; or &quot;event_name&quot; column. Other columns become event properties.
          </p>
          <input ref={fileRef} type="file" accept=".csv" style={{ display: "none" }} onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) csvMutation.mutate(file);
          }} />
          <button className="btn-secondary" onClick={() => fileRef.current?.click()} style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <Upload size={16} /> Choose CSV File
          </button>
          {csvMutation.isSuccess && (
            <p style={{ marginTop: 12, fontSize: 13, color: "var(--accent-emerald)" }}>
              ✓ CSV ingested: {(csvMutation.data as any)?.data?.ingested} events
            </p>
          )}
        </div>
      )}
    </div>
  );
}
