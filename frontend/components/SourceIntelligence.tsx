"use client";

import { CheckCircle, AlertTriangle, ShieldCheck, Activity, HelpCircle } from "lucide-react";

interface Source {
  name: string;
  type: string;
  reliability: number;
  status: "active" | "degraded" | "inactive";
  jobsDiscovered: number;
  lastScan: string;
}

export default function SourceIntelligence() {
  const sources: Source[] = [
    { name: "Greenhouse API", type: "ATS Crawler", reliability: 98, status: "active", jobsDiscovered: 412, lastScan: "Today, 07:00 AM" },
    { name: "Lever API", type: "ATS Crawler", reliability: 97, status: "active", jobsDiscovered: 284, lastScan: "Today, 07:00 AM" },
    { name: "Workday Adapter", type: "Web Adapter", reliability: 91, status: "active", jobsDiscovered: 189, lastScan: "Today, 07:00 AM" },
    { name: "LinkedIn Jobs", type: "Search Engine", reliability: 89, status: "degraded", jobsDiscovered: 74, lastScan: "Yesterday" },
    { name: "Wellfound (AngelList)", type: "Startup API", reliability: 95, status: "active", jobsDiscovered: 38, lastScan: "Today, 07:00 AM" },
    { name: "Direct Company Careers", type: "Web Scraper", reliability: 94, status: "active", jobsDiscovered: 10, lastScan: "Today, 07:00 AM" }
  ];

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "active":
        return <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold bg-emerald-100 text-emerald-700"><CheckCircle size={12} /> Active</span>;
      case "degraded":
        return <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold bg-amber-100 text-amber-700"><AlertTriangle size={12} /> Degraded</span>;
      default:
        return <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold bg-rose-100 text-rose-700"><Activity size={12} /> Inactive</span>;
    }
  };

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
      {sources.map(source => (
        <div key={source.name} className="glass-card rounded-2xl p-6 border border-border-light/40 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-wider text-graphite-light">{source.type}</span>
              {getStatusBadge(source.status)}
            </div>
            <h3 className="text-lg font-bold text-graphite mt-3">{source.name}</h3>
            <p className="text-xs text-graphite-light mt-1 flex items-center gap-1">
              <span>Last Sync: {source.lastScan}</span>
            </p>
          </div>

          <div className="mt-6 pt-4 border-t border-border-light/20 flex items-center justify-between text-xs">
            <div>
              <div className="font-semibold text-graphite-light">Crawl Reliability</div>
              <div className="font-extrabold text-sm text-graphite mt-0.5">{source.reliability}%</div>
            </div>
            <div className="text-right">
              <div className="font-semibold text-graphite-light">Jobs Found</div>
              <div className="font-extrabold text-sm text-graphite mt-0.5">{source.jobsDiscovered}</div>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
