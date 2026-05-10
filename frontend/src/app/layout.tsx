import type { Metadata } from "next";
import "./globals.css";
import { Providers } from "@/lib/providers";

export const metadata: Metadata = {
  title: "Analytics Platform — Real-Time Insights",
  description: "Production-grade real-time analytics and reporting platform. Ingest data, visualize metrics, set alerts, and generate reports.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="light" data-theme="light" style={{ colorScheme: "light" }}>
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet" />
      </head>
      <body style={{ background: "#f8f9fc", color: "#1a1a2e" }}>
        <Providers>
          <div className="animated-bg" />
          {children}
        </Providers>
      </body>
    </html>
  );
}
