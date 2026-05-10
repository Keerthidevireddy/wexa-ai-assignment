"use client";
import { useState, useCallback, useRef, useEffect } from "react";
import { useWebSocket } from "@/lib/websocket";
import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";
import { Activity, Wifi, WifiOff, Pause, Play, Trash2 } from "lucide-react";

interface LiveEvent {
  id: string;
  type: string;
  name?: string;
  data?: Record<string, unknown>;
  timestamp: string;
}

export default function LiveStreamPage() {
  const [events, setEvents] = useState<LiveEvent[]>([]);
  const [paused, setPaused] = useState(false);
  const [filter, setFilter] = useState("");
  const scrollRef = useRef<HTMLDivElement>(null);

  const onMessage = useCallback(
    (msg: any) => {
      if (paused) return;
      const event: LiveEvent = {
        id: crypto.randomUUID(),
        type: msg.type || "event",
        name: msg.event_name || msg.type,
        data: msg,
        timestamp: new Date().toISOString(),
      };
      setEvents((prev) => [event, ...prev].slice(0, 200));
    },
    [paused]
  );

  const { connected } = useWebSocket(onMessage);

  // Also poll recent events for the stream
  const { data: recentEvents } = useQuery({
    queryKey: ["live-recent"],
    queryFn: () => api.get("/events/recent?limit=20").then((r) => r.data),
    refetchInterval: paused ? false : 3000,
  });

  // Seed initial events from API
  useEffect(() => {
    if (recentEvents && events.length === 0) {
      setEvents(
        recentEvents.map((e: any) => ({
          id: e.id,
          type: "event",
          name: e.name,
          data: e.properties,
          timestamp: e.created_at,
        }))
      );
    }
  }, [recentEvents, events.length]);

  const filteredEvents = filter
    ? events.filter((e) => e.name?.toLowerCase().includes(filter.toLowerCase()))
    : events;

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 32 }}>
        <div>
          <h1 style={{ fontSize: 28, fontWeight: 700, marginBottom: 4, display: "flex", alignItems: "center", gap: 12 }}>
            Live Stream
            <span style={{ display: "inline-flex", alignItems: "center", gap: 6, fontSize: 13, fontWeight: 500, color: connected ? "var(--accent-emerald)" : "var(--accent-rose)" }}>
              {connected ? (
                <>
                  <div className="pulse-dot" />
                  Connected
                </>
              ) : (
                <>
                  <WifiOff size={14} />
                  Disconnected
                </>
              )}
            </span>
          </h1>
          <p style={{ color: "var(--text-secondary)", fontSize: 14 }}>
            Watch incoming events in real-time
          </p>
        </div>
        <div style={{ display: "flex", gap: 10 }}>
          <input
            className="input-field"
            placeholder="Filter events..."
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            style={{ width: 200 }}
          />
          <button
            className={paused ? "btn-primary" : "btn-secondary"}
            onClick={() => setPaused(!paused)}
            style={{ display: "flex", alignItems: "center", gap: 6 }}
          >
            {paused ? <Play size={14} /> : <Pause size={14} />}
            {paused ? "Resume" : "Pause"}
          </button>
          <button
            className="btn-secondary"
            onClick={() => setEvents([])}
            style={{ display: "flex", alignItems: "center", gap: 6 }}
          >
            <Trash2 size={14} /> Clear
          </button>
        </div>
      </div>

      {/* Event stream */}
      <div
        ref={scrollRef}
        className="glass-card"
        style={{
          height: "calc(100vh - 220px)",
          overflow: "auto",
          padding: 0,
          fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
          fontSize: 12,
        }}
      >
        {/* Header row */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "140px 140px 1fr",
            padding: "12px 20px",
            borderBottom: "1px solid var(--border-color)",
            position: "sticky",
            top: 0,
            background: "var(--bg-card)",
            zIndex: 2,
            fontSize: 11,
            fontWeight: 600,
            color: "var(--text-secondary)",
            textTransform: "uppercase",
            letterSpacing: "0.04em",
          }}
        >
          <span>Timestamp</span>
          <span>Event</span>
          <span>Data</span>
        </div>

        {filteredEvents.length === 0 ? (
          <div style={{ padding: 48, textAlign: "center", color: "var(--text-muted)" }}>
            <Activity size={32} style={{ margin: "0 auto 12px", opacity: 0.4 }} />
            <p>{paused ? "Stream paused" : "Waiting for events..."}</p>
          </div>
        ) : (
          filteredEvents.map((event, idx) => (
            <div
              key={event.id}
              style={{
                display: "grid",
                gridTemplateColumns: "140px 140px 1fr",
                padding: "10px 20px",
                borderBottom: "1px solid var(--border-color)",
                animation: idx === 0 && !paused ? "fadeIn 0.3s ease" : undefined,
                transition: "background 0.2s",
              }}
              onMouseEnter={(e) => (e.currentTarget.style.background = "rgba(99, 102, 241, 0.04)")}
              onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
            >
              <span style={{ color: "var(--text-muted)" }}>
                {new Date(event.timestamp).toLocaleTimeString()}
              </span>
              <span style={{ color: "var(--accent-cyan)", fontWeight: 500 }}>
                {event.name}
              </span>
              <span style={{ color: "var(--text-secondary)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                {JSON.stringify(event.data)}
              </span>
            </div>
          ))
        )}
        <style>{`@keyframes fadeIn { from { opacity: 0; transform: translateY(-4px); } to { opacity: 1; transform: translateY(0); } }`}</style>
      </div>
    </div>
  );
}
