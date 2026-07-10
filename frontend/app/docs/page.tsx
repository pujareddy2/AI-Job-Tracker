"use client";

import Link from "next/link";
import { Terminal, BookOpen, Layers, Cpu, Sliders, CheckCircle, FileSpreadsheet, Mail, Activity, ArrowLeft } from "lucide-react";

export default function Docs() {
  return (
    <div className="min-h-screen bg-softwhite gradient-mesh flex flex-col antialiased">
      {/* Premium Navbar */}
      <header className="sticky top-0 z-50 glass-card border-b border-border-light/40 py-4 px-6 md:px-12 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="h-9 w-9 rounded-xl bg-gradient-to-tr from-primary to-accent flex items-center justify-center text-white font-bold shadow-md shadow-primary/20">
            C
          </div>
          <div>
            <span className="font-extrabold text-lg text-graphite tracking-tight bg-clip-text bg-gradient-to-r from-graphite to-graphite-light">
              CareerPilot
            </span>
            <span className="font-bold text-xs px-2 py-0.5 rounded-full bg-accent/10 text-accent ml-2">
              AI
            </span>
          </div>
        </div>

        <nav className="flex items-center gap-8 text-sm font-semibold text-graphite-light">
          <Link href="/" className="flex items-center gap-1.5 hover:text-primary transition-colors">
            <ArrowLeft size={16} /> Back to Home
          </Link>
          <Link href="/dashboard" className="hover:text-primary transition-colors">Live Dashboard</Link>
        </nav>
      </header>

      {/* Docs Content */}
      <main className="flex-1 max-w-4xl w-full mx-auto py-16 px-6">
        <div className="flex items-center gap-2.5 px-3 py-1 rounded-full bg-primary/10 text-primary text-xs font-bold w-fit mb-4">
          <BookOpen size={12} /> API & System Documentation
        </div>
        <h1 className="text-4xl md:text-5xl font-extrabold text-graphite tracking-tight mb-8">
          System Reference Manual
        </h1>

        <div className="flex flex-col gap-8">
          {/* Main Docs Card */}
          <div className="glass-card rounded-3xl p-8 border border-border-light/40">
            <h3 className="text-xl font-bold text-graphite flex items-center gap-2">
              <Terminal size={18} className="text-primary" /> Getting Started Overview
            </h3>
            <p className="text-sm text-graphite-light mt-3 leading-relaxed">
              CareerPilot AI interfaces Next.js 15 app router with a Python FastAPI server. The automation orchestrator runs on a custom cron script executed inside GitHub actions every morning. It pulls resume structures, searches job engines, deduplicates entries, performs matching, and synchronizes spreadsheet layers.
            </p>

            <div className="mt-8 border-t border-border-light/40 pt-6">
              <h4 className="font-bold text-sm text-graphite">Folder Hierarchy</h4>
              <pre className="bg-graphite text-white/90 p-4 rounded-xl text-xs font-mono mt-3 overflow-x-auto leading-relaxed">
{`AI-Job-Tracker/
├── application_assistant/   # Automated form filler & profile manager
├── dashboard_backend/       # FastAPI server & metrics calculation
├── filters/                 # Modular filtering & Confidence Engine
├── observability_engine/     # Telemetry logging & validation reports
├── scheduler/               # Stage runner & checkpoint orchestrator
└── frontend/                # Next.js 15 client dashboard (You are here!)`}
              </pre>
            </div>
          </div>

          {/* Architecture Details Card */}
          <div className="glass-card rounded-3xl p-8 border border-border-light/40">
            <h3 className="text-xl font-bold text-graphite flex items-center gap-2">
              <Layers size={18} className="text-accent" /> Architecture Decisions
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-4 text-xs text-graphite-light leading-relaxed">
              <div className="p-5 rounded-2xl bg-white/40 border border-border-light/20">
                <h4 className="font-bold text-sm text-graphite mb-2">Why FastAPI?</h4>
                FastAPI provides high-speed ASGI routing, native data validation via Pydantic, and automatic documentation generation. This ensures the background python workers can instantly load, sync, and validate candidate data.
              </div>
              <div className="p-5 rounded-2xl bg-white/40 border border-border-light/20">
                <h4 className="font-bold text-sm text-graphite mb-2">Why GitHub Actions?</h4>
                Exposing the pipeline on a scheduled cron runner keeps operations 100% decentralized and cost-free, executing autonomously every morning at 7:00 AM IST.
              </div>
            </div>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="py-8 border-t border-border-light/30 px-6 md:px-12 flex justify-between items-center bg-white/40 text-xs text-graphite-light">
        <div>
          &copy; 2026 CareerPilot AI. All rights reserved.
        </div>
        <div className="flex gap-6 font-semibold">
          <Link href="/" className="hover:text-primary">Home</Link>
          <Link href="/dashboard" className="hover:text-primary">Live Dashboard</Link>
        </div>
      </footer>
    </div>
  );
}
