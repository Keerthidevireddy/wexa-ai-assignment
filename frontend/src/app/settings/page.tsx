"use client";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import api from "@/lib/api";
import { useAuthStore } from "@/store/auth";
import { Key, Copy, Trash2, Plus, User, Shield, Building } from "lucide-react";

export default function SettingsPage() {
  const { user } = useAuthStore();
  const queryClient = useQueryClient();
  const [keyName, setKeyName] = useState("");
  const [newKey, setNewKey] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const { data: apiKeys, isLoading } = useQuery({
    queryKey: ["api-keys"],
    queryFn: () => api.get("/auth/api-keys").then((r) => r.data),
  });

  const createKeyMutation = useMutation({
    mutationFn: (name: string) => api.post("/auth/api-keys", { name }),
    onSuccess: (res) => {
      queryClient.invalidateQueries({ queryKey: ["api-keys"] });
      setNewKey(res.data.raw_key);
      setKeyName("");
    },
  });

  const revokeKeyMutation = useMutation({
    mutationFn: (id: string) => api.delete(`/auth/api-keys/${id}`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["api-keys"] }),
  });

  const copyKey = (key: string) => {
    navigator.clipboard.writeText(key);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div style={{ maxWidth: 700 }}>
      <h1 style={{ fontSize: 28, fontWeight: 700, marginBottom: 8 }}>Settings</h1>
      <p style={{ color: "var(--text-secondary)", fontSize: 14, marginBottom: 32 }}>
        Manage your account, organization, and API keys
      </p>

      {/* Profile Section */}
      <div className="glass-card" style={{ padding: 28, marginBottom: 20 }}>
        <h2 style={{ fontSize: 16, fontWeight: 600, marginBottom: 20, display: "flex", alignItems: "center", gap: 8 }}>
          <User size={18} /> Profile
        </h2>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
          <div>
            <label style={{ fontSize: 12, color: "var(--text-muted)", display: "block", marginBottom: 4 }}>Full Name</label>
            <div style={{ fontSize: 14, fontWeight: 500 }}>{user?.full_name || "—"}</div>
          </div>
          <div>
            <label style={{ fontSize: 12, color: "var(--text-muted)", display: "block", marginBottom: 4 }}>Email</label>
            <div style={{ fontSize: 14, fontWeight: 500 }}>{user?.email}</div>
          </div>
          <div>
            <label style={{ fontSize: 12, color: "var(--text-muted)", display: "block", marginBottom: 4 }}>Role</label>
            <span className="badge badge-active" style={{ textTransform: "capitalize" }}>
              <Shield size={10} /> {user?.role}
            </span>
          </div>
          <div>
            <label style={{ fontSize: 12, color: "var(--text-muted)", display: "block", marginBottom: 4 }}>Organization ID</label>
            <div style={{ fontSize: 12, fontFamily: "monospace", color: "var(--text-secondary)" }}>{user?.org_id}</div>
          </div>
        </div>
      </div>

      {/* API Keys Section */}
      <div className="glass-card" style={{ padding: 28 }}>
        <h2 style={{ fontSize: 16, fontWeight: 600, marginBottom: 20, display: "flex", alignItems: "center", gap: 8 }}>
          <Key size={18} /> API Keys
        </h2>
        <p style={{ fontSize: 13, color: "var(--text-secondary)", marginBottom: 20 }}>
          Use API keys to authenticate data ingestion from your applications.
        </p>

        {/* Create key */}
        <div style={{ display: "flex", gap: 10, marginBottom: 20 }}>
          <input
            className="input-field"
            placeholder="Key name (e.g. Production)"
            value={keyName}
            onChange={(e) => setKeyName(e.target.value)}
            style={{ flex: 1 }}
          />
          <button
            className="btn-primary"
            onClick={() => createKeyMutation.mutate(keyName)}
            disabled={!keyName || createKeyMutation.isPending}
            style={{ display: "flex", alignItems: "center", gap: 6, whiteSpace: "nowrap" }}
          >
            <Plus size={14} /> Generate Key
          </button>
        </div>

        {/* Newly created key warning */}
        {newKey && (
          <div style={{ background: "rgba(245, 158, 11, 0.08)", border: "1px solid rgba(245, 158, 11, 0.2)", borderRadius: 12, padding: 16, marginBottom: 20 }}>
            <p style={{ fontSize: 12, color: "var(--accent-amber)", fontWeight: 600, marginBottom: 8 }}>
              ⚠ Copy your API key now. It won&apos;t be shown again!
            </p>
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <code style={{ flex: 1, fontSize: 12, color: "var(--text-primary)", background: "rgba(0,0,0,0.2)", padding: "8px 12px", borderRadius: 8, overflow: "auto" }}>
                {newKey}
              </code>
              <button className="btn-secondary" onClick={() => copyKey(newKey)} style={{ padding: "8px 12px", fontSize: 12, flexShrink: 0 }}>
                <Copy size={14} /> {copied ? "Copied!" : "Copy"}
              </button>
            </div>
          </div>
        )}

        {/* Keys list */}
        {isLoading ? (
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {[1, 2].map((i) => <div key={i} className="skeleton" style={{ height: 48 }} />)}
          </div>
        ) : apiKeys?.length > 0 ? (
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {apiKeys.map((key: any) => (
              <div key={key.id} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "12px 16px", background: "var(--bg-card-hover)", borderRadius: 10, border: "1px solid var(--border-color)" }}>
                <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                  <Key size={14} style={{ color: "var(--text-muted)" }} />
                  <div>
                    <div style={{ fontSize: 13, fontWeight: 500 }}>{key.name}</div>
                    <div style={{ fontSize: 11, color: "var(--text-muted)", fontFamily: "monospace" }}>
                      {key.key_prefix}••••••••
                    </div>
                  </div>
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                  <span style={{ fontSize: 11, color: "var(--text-muted)" }}>
                    {new Date(key.created_at).toLocaleDateString()}
                  </span>
                  <button
                    onClick={() => { if (confirm("Revoke this key?")) revokeKeyMutation.mutate(key.id); }}
                    style={{ background: "none", border: "none", cursor: "pointer", color: "var(--text-muted)", padding: 4 }}
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p style={{ fontSize: 13, color: "var(--text-muted)", textAlign: "center", padding: 20 }}>
            No API keys yet
          </p>
        )}
      </div>
    </div>
  );
}
