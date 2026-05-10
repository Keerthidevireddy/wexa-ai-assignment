"use client";
import Link from "next/link";
import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/store/auth";
import { Zap, BarChart3, Bell, Activity, Database, ArrowRight, Shield, Layers } from "lucide-react";

export default function HomePage() {
  const { isAuthenticated, isLoading, loadUser } = useAuthStore();
  const router = useRouter();

  useEffect(() => {
    loadUser();
  }, [loadUser]);

  useEffect(() => {
    if (!isLoading && isAuthenticated) {
      router.push("/dashboard");
    }
  }, [isLoading, isAuthenticated, router]);

  const features = [
    { icon: Database, title: "Data Ingestion", desc: "REST API, CSV uploads, webhooks with Pydantic validation" },
    { icon: BarChart3, title: "Dashboards", desc: "Custom widgets — line, bar, pie charts and KPI cards" },
    { icon: Bell, title: "Smart Alerts", desc: "Threshold-based alerts with in-app, email & webhook channels" },
    { icon: Activity, title: "Real-Time", desc: "WebSocket live updates and event stream viewer" },
    { icon: Shield, title: "Multi-Tenancy", desc: "Role-based access control with org-level data isolation" },
    { icon: Layers, title: "API Keys", desc: "Generate, rotate, and revoke keys per organization" },
  ];

  return (
    <div style={{ minHeight: "100vh" }}>
      {/* Nav */}
      <nav style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "20px 48px", borderBottom: "1px solid var(--border-color)" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <div style={{ width: 36, height: 36, borderRadius: 10, background: "var(--gradient-primary)", display: "flex", alignItems: "center", justifyContent: "center" }}>
            <Zap size={18} color="white" />
          </div>
          <span style={{ fontWeight: 800, fontSize: 20, letterSpacing: "-0.02em" }}>Analytics Platform</span>
        </div>
        <div style={{ display: "flex", gap: 12 }}>
          <Link href="/login">
            <button className="btn-secondary">Sign in</button>
          </Link>
          <Link href="/signup">
            <button className="btn-primary" style={{ display: "flex", alignItems: "center", gap: 6 }}>
              Get Started <ArrowRight size={14} />
            </button>
          </Link>
        </div>
      </nav>

      {/* Hero */}
      <section style={{ textAlign: "center", padding: "100px 48px 60px", maxWidth: 800, margin: "0 auto" }}>
        <div style={{ display: "inline-flex", alignItems: "center", gap: 8, padding: "6px 16px", borderRadius: 20, background: "rgba(99, 102, 241, 0.1)", border: "1px solid rgba(99, 102, 241, 0.2)", fontSize: 13, color: "var(--accent-blue)", fontWeight: 500, marginBottom: 24 }}>
          <Zap size={14} /> Production-grade analytics
        </div>
        <h1 style={{ fontSize: 56, fontWeight: 800, lineHeight: 1.1, marginBottom: 20, letterSpacing: "-0.03em" }}>
          Real-Time Analytics
          <br />
          <span style={{ background: "var(--gradient-primary)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>
            & Reporting Platform
          </span>
        </h1>
        <p style={{ fontSize: 18, color: "var(--text-secondary)", lineHeight: 1.6, maxWidth: 560, margin: "0 auto 40px" }}>
          Ingest data from multiple sources, visualize metrics through customizable dashboards, set up intelligent alerts, and generate scheduled reports.
        </p>
        <div style={{ display: "flex", gap: 16, justifyContent: "center" }}>
          <Link href="/signup">
            <button className="btn-primary" style={{ padding: "14px 36px", fontSize: 16, display: "flex", alignItems: "center", gap: 8 }}>
              Start Free <ArrowRight size={16} />
            </button>
          </Link>
          <Link href="/login">
            <button className="btn-secondary" style={{ padding: "14px 36px", fontSize: 16 }}>
              View Demo
            </button>
          </Link>
        </div>
      </section>

      {/* Features Grid */}
      <section style={{ padding: "40px 48px 100px", maxWidth: 1000, margin: "0 auto" }}>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 20 }}>
          {features.map((f, i) => (
            <div key={i} className="glass-card" style={{ padding: 28 }}>
              <div style={{ width: 44, height: 44, borderRadius: 12, background: "rgba(99, 102, 241, 0.1)", display: "flex", alignItems: "center", justifyContent: "center", marginBottom: 16, color: "var(--accent-blue)" }}>
                <f.icon size={20} />
              </div>
              <h3 style={{ fontSize: 16, fontWeight: 600, marginBottom: 8 }}>{f.title}</h3>
              <p style={{ fontSize: 13, color: "var(--text-secondary)", lineHeight: 1.6 }}>{f.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Tech Stack */}
      <section style={{ padding: "40px 48px 80px", textAlign: "center", borderTop: "1px solid var(--border-color)" }}>
        <p style={{ fontSize: 13, color: "var(--text-muted)", marginBottom: 20, textTransform: "uppercase", letterSpacing: "0.06em" }}>
          Built with
        </p>
        <div style={{ display: "flex", justifyContent: "center", gap: 32, flexWrap: "wrap", color: "var(--text-secondary)", fontSize: 14, fontWeight: 500 }}>
          {["FastAPI", "Next.js", "PostgreSQL", "Redis", "Celery", "SQLAlchemy", "WebSockets", "Pydantic"].map((t) => (
            <span key={t} style={{ padding: "8px 16px", background: "var(--bg-card)", borderRadius: 8, border: "1px solid var(--border-color)" }}>
              {t}
            </span>
          ))}
        </div>
      </section>
    </div>
  );
}
