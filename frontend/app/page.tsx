"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import { 
  Sparkles, 
  ArrowRight, 
  BookOpen, 
  Layers, 
  Cpu, 
  Search, 
  Sliders, 
  CheckCircle, 
  FileSpreadsheet, 
  Mail, 
  Terminal, 
  Zap, 
  Activity 
} from "lucide-react";
import { useState, useEffect } from "react";

// SVGs for diagram animations
function ConnectionLine({ className }: { className?: string }) {
  return (
    <svg className={`absolute inset-0 w-full h-full pointer-events-none ${className}`} style={{ minHeight: "100px" }}>
      <line x1="50%" y1="0%" x2="50%" y2="100%" stroke="url(#cyan-violet-grad)" strokeWidth="2" strokeDasharray="5,5" className="animate-[dash_2s_linear_infinite]" />
      <defs>
        <linearGradient id="cyan-violet-grad" x1="0%" y1="0%" x2="0%" y2="100%">
          <stop offset="0%" stopColor="#10b981" />
          <stop offset="50%" stopColor="#06b6d4" />
          <stop offset="100%" stopColor="#7c3aed" />
        </linearGradient>
      </defs>
    </svg>
  );
}

export default function Home() {
  const [stats, setStats] = useState({
    jobsScanned: 0,
    resumeMatches: 0,
    successRate: 0,
    sourcesScan: 0
  });

  useEffect(() => {
    // Count-up animations for statistics
    const duration = 1500;
    const steps = 50;
    const stepTime = duration / steps;
    let step = 0;

    const timer = setInterval(() => {
      step++;
      setStats({
        jobsScanned: Math.floor((1007 / steps) * step),
        resumeMatches: Math.floor((942 / steps) * step),
        successRate: Math.floor((98 / steps) * step),
        sourcesScan: Math.floor((12 / steps) * step)
      });

      if (step >= steps) {
        clearInterval(timer);
        setStats({
          jobsScanned: 1007,
          resumeMatches: 942,
          successRate: 98.7,
          sourcesScan: 12
        });
      }
    }, stepTime);

    return () => clearInterval(timer);
  }, []);

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

        <nav className="hidden md:flex items-center gap-8 text-sm font-medium text-graphite-light">
          <a href="#features" className="hover:text-primary transition-colors">Features</a>
          <a href="#architecture" className="hover:text-primary transition-colors">Architecture</a>
          <Link href="/dashboard" className="hover:text-primary transition-colors">Live Dashboard</Link>
          <a href="#docs" className="hover:text-primary transition-colors">Docs</a>
        </nav>

        <div className="flex items-center gap-4">
          <Link 
            href="/dashboard" 
            className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-gradient-to-r from-primary to-accent hover:from-primary-hover hover:to-accent-hover text-white text-sm font-semibold shadow-md shadow-primary/10 transition-all duration-300 transform hover:scale-[1.02]"
          >
            Launch Dashboard <ArrowRight size={16} />
          </Link>
        </div>
      </header>

      {/* Hero Section */}
      <section className="relative pt-20 pb-16 px-6 md:px-12 max-w-7xl mx-auto flex flex-col items-center text-center">
        {/* Animated Badge */}
        <motion.div 
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-white/80 border border-primary/20 shadow-sm shadow-primary/5 text-xs font-semibold text-primary mb-6"
        >
          <Sparkles size={12} className="text-accent animate-pulse" />
          <span>Autonomous Career Intelligence OS</span>
        </motion.div>

        {/* Hero Headline */}
        <motion.h1 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 0.1 }}
          className="text-4xl md:text-6xl lg:text-7xl font-extrabold text-graphite tracking-tight leading-[1.1] max-w-4xl"
        >
          Your Career Search. <br />
          <span className="bg-clip-text text-transparent bg-gradient-to-r from-primary via-accent to-secondary">
            On Autopilot.
          </span>
        </motion.h1>

        {/* Subtitle */}
        <motion.p 
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.8, delay: 0.3 }}
          className="mt-6 text-lg md:text-xl text-graphite-light max-w-2xl font-normal leading-relaxed"
        >
          AI-powered resume intelligence, verified job discovery, ATS scoring, confidence ranking, analytics and workflow automation.
        </motion.p>

        {/* Call to Actions */}
        <motion.div 
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 0.4 }}
          className="mt-10 flex flex-wrap gap-4 justify-center"
        >
          <Link 
            href="/dashboard"
            className="flex items-center gap-2 px-6 py-3.5 rounded-2xl bg-gradient-to-r from-primary to-accent hover:from-primary-hover hover:to-accent-hover text-white text-base font-bold shadow-lg shadow-primary/10 transition-all duration-300 transform hover:scale-[1.02]"
          >
            Open Live Dashboard
          </Link>
          <a 
            href="https://github.com/pujareddy2/AI-Job-Tracker" 
            target="_blank" 
            rel="noopener noreferrer"
            className="flex items-center gap-2 px-6 py-3.5 rounded-2xl bg-white border border-border-light shadow-sm text-graphite hover:border-graphite/30 hover:bg-softwhite transition-all text-base font-semibold"
          >
            <svg className="h-4.5 w-4.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M15 22v-4a4.8 4.8 0 0 0-1-3.5c3 0 6-2 6-5.5.08-1.25-.27-2.48-1-3.5.28-1.15.28-2.35 0-3.5 0 0-1 0-3 1.5-2.64-.5-5.36-.5-8 0C6 2 5 2 5 2c-.3 1.15-.3 2.35 0 3.5A5.403 5.403 0 0 0 4 9c0 3.5 3 5.5 6 5.5-.39.49-.68 1.05-.85 1.65-.17.6-.22 1.23-.15 1.85v4" /><path d="M9 18c-4.51 2-5-2-7-2" /></svg> GitHub Repository
          </a>
          <a 
            href="#docs" 
            className="flex items-center gap-2 px-6 py-3.5 rounded-2xl bg-white border border-border-light shadow-sm text-graphite hover:border-graphite/30 hover:bg-softwhite transition-all text-base font-semibold"
          >
            <BookOpen size={18} /> Documentation
          </a>
        </motion.div>

        {/* Real-time Counter Stats */}
        <div className="mt-20 w-full max-w-5xl grid grid-cols-2 md:grid-cols-4 gap-6 px-4">
          {[
            { label: "Jobs Scanned", val: stats.jobsScanned, suffix: "+" },
            { label: "Matches Generated", val: stats.resumeMatches, suffix: "" },
            { label: "Success Rate", val: stats.successRate, suffix: "%" },
            { label: "Monitored Sources", val: stats.sourcesScan, suffix: "" }
          ].map((stat, i) => (
            <motion.div 
              key={stat.label}
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: 0.1 * i + 0.4 }}
              className="glass-card rounded-2xl p-6 text-left relative overflow-hidden"
            >
              <div className="absolute top-0 left-0 w-full h-[3px] bg-gradient-to-r from-primary/30 to-accent/30" />
              <div className="text-3xl md:text-4xl font-extrabold text-graphite tracking-tight">
                {stat.val}{stat.suffix}
              </div>
              <div className="text-sm font-medium text-graphite-light mt-1">
                {stat.label}
              </div>
            </motion.div>
          ))}
        </div>
      </section>

      {/* Interactive SVG Architecture Section */}
      <section id="architecture" className="py-20 bg-white/60 border-y border-border-light/40 relative overflow-hidden">
        <div className="max-w-7xl mx-auto px-6 md:px-12 text-center">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-secondary/10 text-secondary text-xs font-semibold mb-3">
            <Layers size={12} /> System Pipeline Flow
          </div>
          <h2 className="text-3xl md:text-5xl font-extrabold text-graphite tracking-tight mb-4">
            Visual Architecture Diagram
          </h2>
          <p className="text-graphite-light max-w-xl mx-auto mb-16">
            Witness the autonomous flow of career intelligence processing telemetry from source to sheet.
          </p>

          {/* SVG Animated Architecture */}
          <div className="max-w-4xl mx-auto glass-card rounded-3xl p-8 relative min-h-[500px] flex flex-col justify-between items-center overflow-hidden">
            {/* Top Node */}
            <div className="relative z-10 w-full flex justify-center mb-8">
              <div className="px-6 py-3 rounded-2xl bg-gradient-to-r from-primary to-accent text-white font-bold shadow-md shadow-primary/20 flex items-center gap-2 border border-primary/20">
                <Sparkles size={16} /> Resume Import
              </div>
            </div>

            {/* Stage Grid Container */}
            <div className="relative z-10 w-full grid grid-cols-2 md:grid-cols-4 gap-4 md:gap-6 my-10">
              {[
                { title: "Job Discovery", desc: "Automated crawling", icon: Search },
                { title: "Source Intelligence", desc: "ATS validation", icon: Cpu },
                { title: "Filtering Pipeline", desc: "11 Modular Filters", icon: Sliders },
                { title: "Confidence Engine", desc: "Recruiter AI scoring", icon: Activity }
              ].map((stage, idx) => (
                <div key={stage.title} className="glass-card rounded-2xl p-5 border border-border-light/40 relative text-left">
                  <div className="h-10 w-10 rounded-xl bg-primary/10 text-primary flex items-center justify-center mb-3">
                    <stage.icon size={20} />
                  </div>
                  <h4 className="font-bold text-graphite text-base">{stage.title}</h4>
                  <p className="text-xs text-graphite-light mt-1">{stage.desc}</p>
                </div>
              ))}
            </div>

            {/* Bottom Output Nodes */}
            <div className="relative z-10 w-full flex flex-col md:flex-row justify-center items-center gap-6 mt-8">
              <div className="px-5 py-3 rounded-xl bg-white border border-border-light shadow-sm flex items-center gap-2">
                <FileSpreadsheet size={16} className="text-green-500" /> Google Sheets Sync
              </div>
              <div className="px-5 py-3 rounded-xl bg-white border border-border-light shadow-sm flex items-center gap-2">
                <Terminal size={16} className="text-purple-500" /> Notion Database
              </div>
              <div className="px-5 py-3 rounded-xl bg-white border border-border-light shadow-sm flex items-center gap-2">
                <Mail size={16} className="text-accent" /> Daily EmailDigest
              </div>
            </div>

            {/* Background running flows */}
            <ConnectionLine className="top-12 h-[350px]" />
          </div>
        </div>
      </section>

      {/* Features Bento Section */}
      <section id="features" className="py-24 px-6 md:px-12 max-w-7xl mx-auto">
        <div className="text-center mb-16">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-primary/10 text-primary text-xs font-semibold mb-3">
            <Zap size={12} /> Autonomous Features
          </div>
          <h2 className="text-3xl md:text-5xl font-extrabold text-graphite tracking-tight mb-4">
            Designed for Peak Performance
          </h2>
          <p className="text-graphite-light max-w-xl mx-auto">
            CareerPilot AI handles the heavy lifting, serving premium modules to optimize and secure your pipeline.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Features cards */}
          {[
            { 
              title: "Resume Intelligence", 
              desc: "Deep profile processing suggesting career domains, extracting complex skill sets, and matching keywords.",
              icon: Cpu, 
              color: "border-primary/20 hover:border-primary/50" 
            },
            { 
              title: "Source Verification", 
              desc: "Monitors and ranks job directories for maximum authenticity, skipping sketchy portals and spam links.",
              icon: Search, 
              color: "border-accent/20 hover:border-accent/50" 
            },
            { 
              title: "Confidence Ranker", 
              desc: "Intelligent weights mapping job suitability (0-100) instead of simple pass/fail rejections.",
              icon: Sliders, 
              color: "border-secondary/20 hover:border-secondary/50" 
            },
            { 
              title: "Observability Pipeline", 
              desc: "Total metrics and funnel rates logs so you know exactly where opportunities are passing or dropping off.",
              icon: Activity, 
              color: "border-highlight/20 hover:border-highlight/50" 
            },
            { 
              title: "Google Sheet & Notion Integration", 
              desc: "Dynamic layout updates and automatic status logs writing directly to sheets and trackers.",
              icon: FileSpreadsheet, 
              color: "border-primary/20 hover:border-primary/50" 
            },
            { 
              title: "Workflow Automation", 
              desc: "GitHub Actions scheduler running daily scans at 7:00 AM IST to keep matches always fresh.",
              icon: Terminal, 
              color: "border-accent/20 hover:border-accent/50" 
            }
          ].map((feat, idx) => (
            <motion.div 
              key={feat.title}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: idx * 0.05 }}
              className={`glass-card glass-card-hover rounded-3xl p-8 border ${feat.color}`}
            >
              <div className="h-12 w-12 rounded-2xl bg-gradient-to-tr from-white to-softwhite shadow-inner flex items-center justify-center mb-6">
                <feat.icon size={22} className="text-graphite" />
              </div>
              <h3 className="text-xl font-bold text-graphite">{feat.title}</h3>
              <p className="text-sm text-graphite-light leading-relaxed mt-3">{feat.desc}</p>
            </motion.div>
          ))}
        </div>
      </section>

      {/* Docs/Documentation Section */}
      <section id="docs" className="py-20 bg-white/60 border-t border-border-light/40">
        <div className="max-w-5xl mx-auto px-6">
          <h2 className="text-3xl font-extrabold text-graphite tracking-tight mb-8">Documentation & Architecture</h2>
          <div className="glass-card rounded-3xl p-8">
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
        </div>
      </section>

      {/* Footer */}
      <footer className="mt-auto py-8 border-t border-border-light/30 px-6 md:px-12 flex flex-col md:flex-row justify-between items-center gap-4 bg-white/40 text-xs text-graphite-light">
        <div>
          &copy; 2026 CareerPilot AI. All rights reserved.
        </div>
        <div className="flex gap-6">
          <a href="#features" className="hover:text-primary">Features</a>
          <a href="#architecture" className="hover:text-primary">Architecture</a>
          <Link href="/dashboard" className="hover:text-primary">Live Dashboard</Link>
        </div>
      </footer>
    </div>
  );
}
