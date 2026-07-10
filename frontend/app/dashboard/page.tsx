"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { 
  LayoutDashboard, 
  Briefcase, 
  Cpu, 
  Activity, 
  Terminal, 
  BarChart4, 
  ShieldCheck, 
  FileText, 
  BookOpen, 
  Info, 
  LogOut, 
  User, 
  AlertCircle, 
  TrendingUp, 
  Search,
  Sparkles,
  Layers,
  ArrowUpRight,
  ExternalLink,
  ChevronRight
} from "lucide-react";

import JobTable from "@/components/JobTable";
import AnalyticsCharts from "@/components/AnalyticsCharts";
import ResumeIntelligence from "@/components/ResumeIntelligence";
import SourceIntelligence from "@/components/SourceIntelligence";
import AutomationFlow from "@/components/AutomationFlow";
import ObservabilityView from "@/components/ObservabilityView";

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || "http://127.0.0.1:8000";

interface ActionItem {
  category: string;
  message: string;
  urgency: string;
  job_id: string | null;
}

interface DashboardStats {
  candidate_name: string;
  pipeline_status: string;
  last_sync_time: string;
  overall_score: number;
  metrics: {
    career_health_score: number;
    total_jobs: number;
    applied_count: number;
    matching_average: number;
    ats_average: number;
  };
  funnel: {
    saved: number;
    applied: number;
    assessment: number;
    technical: number;
    hr: number;
    offer: number;
  };
  action_items: ActionItem[];
  ai_recommendations: string[];
}

type TabType = "overview" | "jobs" | "resume" | "sources" | "automation" | "analytics" | "observability" | "reports" | "docs" | "about";

export default function Dashboard() {
  const [activeTab, setActiveTab] = useState<TabType>("overview");
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchStats = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${BACKEND_URL}/api/dashboard/stats`);
      if (res.ok) {
        const data = await res.json();
        setStats(data);
      } else {
        throw new Error("Stats fetch failed");
      }
    } catch (e) {
      console.warn("FastAPI Server offline or not found, using mockup metrics.", e);
      // Premium Mockup stats matching exact FastAPI return schema
      setStats({
        candidate_name: "Puja Midde",
        pipeline_status: "Standby",
        last_sync_time: "Today, 07:00 AM",
        overall_score: 87,
        metrics: {
          career_health_score: 87,
          total_jobs: 1007,
          applied_count: 32,
          matching_average: 84,
          ats_average: 79
        },
        funnel: {
          saved: 24,
          applied: 14,
          assessment: 6,
          technical: 8,
          hr: 2,
          offer: 2
        },
        action_items: [
          { category: "Apply Today", message: "Apply for Applied AI Engineer at Google AI", urgency: "High", job_id: "job-1" },
          { category: "Skills To Learn", message: "Build a Pinecone/Chroma RAG backend application (~2 weeks required)", urgency: "Medium", job_id: null },
          { category: "Resume Needs Improvement", message: "Add more FastAPI metrics logging experience", urgency: "High", job_id: null }
        ],
        ai_recommendations: [
          "Apply to Google AI and Microsoft Research matches today (90%+ Confidence scores).",
          "FastAPI and Python backend market demand increased by 12% in Hyderabad this week.",
          "Add RAG / Vector Search to your resume to increase matches by up to 28%."
        ]
      });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStats();
  }, []);

  const menuItems = [
    { id: "overview", label: "Overview", icon: LayoutDashboard },
    { id: "jobs", label: "Job Intelligence", icon: Briefcase },
    { id: "resume", label: "Resume AI", icon: Cpu },
    { id: "sources", label: "Source Intelligence", icon: ShieldCheck },
    { id: "automation", label: "Automation Center", icon: Terminal },
    { id: "analytics", label: "Analytics Charts", icon: BarChart4 },
    { id: "observability", label: "Telemetry & Logs", icon: Activity },
    { id: "reports", label: "SaaS Reports", icon: FileText },
    { id: "docs", label: "Documentation", icon: BookOpen },
    { id: "about", label: "About System", icon: Info }
  ];

  return (
    <div className="min-h-screen bg-softwhite flex">
      {/* Sidebar Navigation */}
      <aside className="w-64 glass-card border-r border-border-light/40 flex flex-col justify-between shrink-0 p-6">
        <div>
          {/* Sidebar Logo */}
          <Link href="/" className="flex items-center gap-3 mb-10">
            <div className="h-8 w-8 rounded-xl bg-gradient-to-tr from-primary to-accent flex items-center justify-center text-white font-bold">
              C
            </div>
            <div>
              <span className="font-extrabold text-base text-graphite tracking-tight">CareerPilot</span>
              <span className="font-bold text-xs bg-accent/10 text-accent px-1.5 py-0.5 rounded ml-1.5">AI</span>
            </div>
          </Link>

          {/* Nav Items */}
          <nav className="flex flex-col gap-1.5">
            {menuItems.map(item => (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id as TabType)}
                className={`w-full flex items-center gap-3.5 px-4 py-3 rounded-xl text-sm font-semibold transition-all text-left ${
                  activeTab === item.id 
                    ? "bg-gradient-to-r from-primary/10 to-accent/10 text-primary border-l-[3px] border-primary shadow-sm"
                    : "text-graphite-light hover:bg-gray-100/50 hover:text-graphite"
                }`}
              >
                <item.icon size={18} className={activeTab === item.id ? "text-primary" : "text-graphite-light"} />
                {item.label}
              </button>
            ))}
          </nav>
        </div>

        {/* User Card */}
        <div className="border-t border-border-light/20 pt-6 flex items-center justify-between gap-3 text-xs">
          <div className="flex items-center gap-3">
            <div className="h-8 w-8 rounded-full bg-primary/10 flex items-center justify-center text-primary font-bold">
              PM
            </div>
            <div className="flex flex-col">
              <span className="font-bold text-graphite text-xs">Puja Midde</span>
              <span className="text-graphite-light font-medium">Candidate</span>
            </div>
          </div>
          <Link href="/" className="text-graphite-light hover:text-rose-500 p-1.5 rounded-lg hover:bg-rose-500/5 transition-all">
            <LogOut size={16} />
          </Link>
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="flex-1 p-6 md:p-12 overflow-y-auto max-h-screen">
        {/* Tab Content Orchestrator */}
        {activeTab === "overview" && (
          <div className="flex flex-col gap-8">
            {/* Title / Header */}
            <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
              <div>
                <h1 className="text-3xl font-extrabold tracking-tight text-graphite">Autonomous Command Center</h1>
                <p className="text-sm font-medium text-graphite-light mt-1">
                  Monitor career matching analytics, actions, and sheet synchronization telemetry.
                </p>
              </div>
              <div className="flex items-center gap-3 text-xs bg-white border border-border-light p-2.5 rounded-xl shadow-sm font-medium">
                <span className="h-2.5 w-2.5 rounded-full bg-emerald-500 animate-ping" />
                <span>Last Crawler Run: {stats?.last_sync_time || "Today, 07:00 AM"}</span>
              </div>
            </div>

            {/* KPI Cards Grid */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
              {[
                { title: "Career Health Score", value: `${stats?.overall_score || 0}%`, label: "Target: >90%", color: "text-primary bg-primary/5" },
                { title: "Total Opportunities Scanned", value: stats?.metrics.total_jobs || 0, label: "All direct crawls", color: "text-accent bg-accent/5" },
                { title: "Average Resume Match", value: `${stats?.metrics.matching_average || 0}%`, label: "Semantic evaluation", color: "text-secondary bg-secondary/5" },
                { title: "Average ATS compatibility", value: `${stats?.metrics.ats_average || 0}%`, label: "Score weighting", color: "text-highlight bg-highlight/5" }
              ].map(kpi => (
                <div key={kpi.title} className="glass-card rounded-2xl p-6 border border-border-light/40 relative overflow-hidden flex flex-col justify-between min-h-[140px]">
                  <div className="absolute top-0 left-0 h-[3px] w-full bg-gradient-to-r from-primary/30 to-accent/30" />
                  <span className="text-xs font-bold uppercase tracking-wider text-graphite-light">{kpi.title}</span>
                  <div className="text-3xl font-extrabold text-graphite tracking-tight mt-3">{kpi.value}</div>
                  <span className="text-xs text-graphite-light mt-2">{kpi.label}</span>
                </div>
              ))}
            </div>

            {/* Lower dashboard modules: Action Center and AI recommendation */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Action items */}
              <div className="glass-card rounded-2xl p-6 border border-border-light/40 flex flex-col lg:col-span-2">
                <h3 className="text-base font-extrabold text-graphite flex items-center gap-2 mb-4">
                  <AlertCircle size={18} className="text-primary" /> Today&apos;s Action Items
                </h3>
                <div className="flex flex-col gap-3">
                  {stats?.action_items.map((item, i) => (
                    <div key={i} className="flex items-start md:items-center justify-between gap-4 p-4 rounded-xl border border-border-light/20 bg-white/40 text-xs">
                      <div>
                        <span className={`inline-flex px-2 py-0.5 rounded-full font-extrabold text-[10px] uppercase tracking-wider ${
                          item.urgency === "High" ? "bg-rose-100 text-rose-700" : "bg-amber-100 text-amber-700"
                        }`}>{item.urgency} Priority</span>
                        <div className="font-bold text-graphite mt-1 text-sm">{item.category}</div>
                        <p className="text-graphite-light mt-0.5 font-medium">{item.message}</p>
                      </div>
                      {item.job_id && (
                        <button 
                          onClick={() => setActiveTab("jobs")}
                          className="flex items-center gap-1 bg-white border border-border-light hover:bg-softwhite px-3.5 py-2 rounded-xl text-xs font-bold text-graphite shadow-sm"
                        >
                          View Job <ChevronRight size={14} />
                        </button>
                      )}
                    </div>
                  ))}
                </div>
              </div>

              {/* Recommendations Panel */}
              <div className="glass-card rounded-2xl p-6 border border-border-light/40 flex flex-col">
                <h3 className="text-base font-extrabold text-graphite flex items-center gap-2 mb-4">
                  <Sparkles size={18} className="text-accent" /> AI Optimization Insights
                </h3>
                <div className="flex flex-col gap-3 text-xs leading-relaxed text-graphite-light">
                  {stats?.ai_recommendations.map((rec, i) => (
                    <div key={i} className="p-3 bg-white/40 rounded-xl border border-border-light/10 font-medium">
                      {rec}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}

        {activeTab === "jobs" && (
          <div>
            <h1 className="text-3xl font-extrabold tracking-tight text-graphite mb-2">Job Intelligence</h1>
            <p className="text-sm font-medium text-graphite-light mb-8">
              Explore discovered job matches, sorted by AI confidence and ATS scores.
            </p>
            <JobTable />
          </div>
        )}

        {activeTab === "resume" && (
          <div>
            <h1 className="text-3xl font-extrabold tracking-tight text-graphite mb-2">Resume Intelligence</h1>
            <p className="text-sm font-medium text-graphite-light mb-8">
              Review parsed skills and recommendations from the optimization report.
            </p>
            <ResumeIntelligence />
          </div>
        )}

        {activeTab === "sources" && (
          <div>
            <h1 className="text-3xl font-extrabold tracking-tight text-graphite mb-2">Source Intelligence</h1>
            <p className="text-sm font-medium text-graphite-light mb-8">
              Check sync latency, jobs scanned, and adapter statuses.
            </p>
            <SourceIntelligence />
          </div>
        )}

        {activeTab === "automation" && (
          <div>
            <h1 className="text-3xl font-extrabold tracking-tight text-graphite mb-2">Automation Center</h1>
            <p className="text-sm font-medium text-graphite-light mb-8">
              Track the GitHub Actions cron pipeline and schedule execution routines.
            </p>
            <AutomationFlow />
          </div>
        )}

        {activeTab === "analytics" && (
          <div>
            <h1 className="text-3xl font-extrabold tracking-tight text-graphite mb-2">Analytics Charts</h1>
            <p className="text-sm font-medium text-graphite-light mb-8">
              Inspect multi-dimensional distributions of job matches and pipeline funnels.
            </p>
            <AnalyticsCharts />
          </div>
        )}

        {activeTab === "observability" && (
          <div>
            <h1 className="text-3xl font-extrabold tracking-tight text-graphite mb-2">Telemetry Observability</h1>
            <p className="text-sm font-medium text-graphite-light mb-8">
              Inspect Phase 22 runtime observability stage telemetry and error diagnostics.
            </p>
            <ObservabilityView />
          </div>
        )}

        {activeTab === "reports" && (
          <div className="flex flex-col gap-6">
            <h1 className="text-3xl font-extrabold tracking-tight text-graphite">SaaS Reports</h1>
            <p className="text-sm font-medium text-graphite-light -mt-4">
              Compile, download, and review daily, weekly, or monthly career tracker summaries.
            </p>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {["Daily Resume Optimization Digest", "Weekly Job Search Metrics Report", "Monthly Career Intelligence Analysis"].map((title, i) => (
                <div key={title} className="glass-card rounded-2xl p-6 border border-border-light/40 flex flex-col justify-between min-h-[220px]">
                  <div>
                    <span className="text-xs font-bold text-primary tracking-wider uppercase">{i === 0 ? "Daily" : i === 1 ? "Weekly" : "Monthly"} Report</span>
                    <h3 className="text-lg font-bold text-graphite mt-3 leading-snug">{title}</h3>
                    <p className="text-xs text-graphite-light mt-1">Generated: Today, 07:00 AM</p>
                  </div>
                  <div className="mt-6 flex flex-wrap gap-2 pt-4 border-t border-border-light/20">
                    <button className="px-3.5 py-2 rounded-xl bg-white border border-border-light hover:bg-softwhite text-xs font-bold text-graphite transition-all shadow-sm">
                      Export CSV
                    </button>
                    <button className="px-3.5 py-2 rounded-xl bg-white border border-border-light hover:bg-softwhite text-xs font-bold text-graphite transition-all shadow-sm">
                      Export PDF
                    </button>
                    <button className="px-3.5 py-2 rounded-xl bg-white border border-border-light hover:bg-softwhite text-xs font-bold text-graphite transition-all shadow-sm">
                      Export JSON
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {activeTab === "docs" && (
          <div className="flex flex-col gap-6 max-w-4xl text-left">
            <h1 className="text-3xl font-extrabold tracking-tight text-graphite">System Documentation</h1>
            <div className="glass-card rounded-2xl p-8 border border-border-light/40 flex flex-col gap-6 leading-relaxed text-sm text-graphite-light">
              <div>
                <h3 className="text-lg font-bold text-graphite flex items-center gap-2">
                  <ShieldCheck size={18} className="text-primary" /> Architecture Paradigm
                </h3>
                <p className="mt-2 text-graphite-light">
                  The frontend fetches data from a Python FastAPI server. The Python background worker runs once per day under a scheduled trigger on GitHub Actions (which schedules main.py with appropriate options).
                </p>
              </div>

              <div>
                <h3 className="text-lg font-bold text-graphite flex items-center gap-2">
                  <Terminal size={18} className="text-primary" /> API Specification
                </h3>
                <ul className="mt-2 flex flex-col gap-2 font-mono text-xs">
                  <li className="bg-white/40 p-2 rounded-xl border border-border-light/20"><span className="text-emerald-600 font-bold">GET</span> /api/dashboard/stats — Aggregated KPI metrics</li>
                  <li className="bg-white/40 p-2 rounded-xl border border-border-light/20"><span className="text-emerald-600 font-bold">GET</span> /api/jobs — Paginated, filtered job matches</li>
                  <li className="bg-white/40 p-2 rounded-xl border border-border-light/20"><span className="text-indigo-600 font-bold">POST</span> /api/applications/status — Update CRM status</li>
                  <li className="bg-white/40 p-2 rounded-xl border border-border-light/20"><span className="text-emerald-600 font-bold">GET</span> /api/skills — Candidate profile parsed skills</li>
                </ul>
              </div>
            </div>
          </div>
        )}

        {activeTab === "about" && (
          <div className="flex flex-col gap-6 max-w-4xl text-left">
            <h1 className="text-3xl font-extrabold tracking-tight text-graphite">About CareerPilot AI</h1>
            <div className="glass-card rounded-2xl p-8 border border-border-light/40 leading-relaxed text-sm text-graphite-light flex flex-col gap-5">
              <p>
                <strong>CareerPilot AI</strong> is an autonomous Career Intelligence Platform designed to eliminate manual job hunting through intelligent crawlers, resume intelligence, and semantic ATS match ratings.
              </p>
              <h3 className="text-lg font-bold text-graphite mt-3">Product Roadmap</h3>
              <ul className="list-disc pl-5 flex flex-col gap-2 text-xs font-semibold text-graphite-light">
                <li>Integrate cover letter optimization draft generation route.</li>
                <li>Extend direct browser autofill form inputs.</li>
                <li>Add Chrome extension client for manual clicks.</li>
              </ul>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
