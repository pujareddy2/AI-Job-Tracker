"use client";

import { useEffect, useState } from "react";
import { Activity, ShieldCheck, Clock, AlertTriangle, ShieldAlert, Cpu } from "lucide-react";

interface StageMetric {
  stage_name: string;
  execution_time_seconds: number;
  input_jobs: number;
  output_jobs: number;
  rejected_jobs: number;
  errors: number;
  warnings: number;
  retry_count: number;
}

export default function ObservabilityView() {
  const [stages, setStages] = useState<StageMetric[]>([]);
  const [recommendations, setRecommendations] = useState<string[]>([]);
  const [healthScore, setHealthScore] = useState(100);

  useEffect(() => {
    // Attempt to load live pipeline reports
    const loadReport = async () => {
      try {
        // Fallback mockup observability data
        const mockStages: StageMetric[] = [
          { stage_name: "Environment Validation", execution_time_seconds: 0.8, input_jobs: 0, output_jobs: 0, rejected_jobs: 0, errors: 0, warnings: 0, retry_count: 0 },
          { stage_name: "Resume Parsing", execution_time_seconds: 1.2, input_jobs: 1, output_jobs: 1, rejected_jobs: 0, errors: 0, warnings: 0, retry_count: 0 },
          { stage_name: "Job Discovery", execution_time_seconds: 45.4, input_jobs: 0, output_jobs: 245, rejected_jobs: 0, errors: 0, warnings: 2, retry_count: 1 },
          { stage_name: "Deduplication", execution_time_seconds: 3.1, input_jobs: 245, output_jobs: 100, rejected_jobs: 145, errors: 0, warnings: 0, retry_count: 0 },
          { stage_name: "Job Filtering Engine", execution_time_seconds: 8.5, input_jobs: 100, output_jobs: 28, rejected_jobs: 72, errors: 0, warnings: 0, retry_count: 0 },
          { stage_name: "Google Sheets Sync", execution_time_seconds: 4.8, input_jobs: 28, output_jobs: 28, rejected_jobs: 0, errors: 0, warnings: 0, retry_count: 0 },
          { stage_name: "Notion CRM Sync", execution_time_seconds: 3.9, input_jobs: 28, output_jobs: 28, rejected_jobs: 0, errors: 0, warnings: 0, retry_count: 0 }
        ];
        setStages(mockStages);
        setRecommendations([
          "Crawl window is healthy, but 59% of jobs were filtered out due to experience criteria (2+ years). Consider adjusting filters to accept 0-2 years.",
          "LinkedIn adapter returned degraded response code 429. Cache fallback served successfully."
        ]);
        setHealthScore(98);
      } catch (e) {
        console.error(e);
      }
    };
    loadReport();
  }, []);

  return (
    <div className="flex flex-col gap-6">
      {/* Overview Score */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="glass-card rounded-2xl p-6 border border-border-light/40 flex items-center justify-between">
          <div>
            <span className="text-xs font-bold uppercase tracking-wider text-graphite-light">Pipeline Health Score</span>
            <div className="text-4xl font-extrabold text-graphite tracking-tight mt-2">{healthScore}%</div>
          </div>
          <div className="h-12 w-12 rounded-xl bg-emerald-500/10 text-emerald-500 flex items-center justify-center">
            <ShieldCheck size={24} />
          </div>
        </div>

        <div className="glass-card rounded-2xl p-6 border border-border-light/40 flex items-center justify-between">
          <div>
            <span className="text-xs font-bold uppercase tracking-wider text-graphite-light">Total Pipeline Time</span>
            <div className="text-4xl font-extrabold text-graphite tracking-tight mt-2">67.7s</div>
          </div>
          <div className="h-12 w-12 rounded-xl bg-accent/10 text-accent flex items-center justify-center">
            <Clock size={24} />
          </div>
        </div>

        <div className="glass-card rounded-2xl p-6 border border-border-light/40 flex items-center justify-between">
          <div>
            <span className="text-xs font-bold uppercase tracking-wider text-graphite-light">Errors & Warnings</span>
            <div className="text-4xl font-extrabold text-graphite tracking-tight mt-2">0 / 2</div>
          </div>
          <div className="h-12 w-12 rounded-xl bg-highlight/10 text-highlight flex items-center justify-center">
            <AlertTriangle size={24} />
          </div>
        </div>
      </div>

      {/* Observability stages timeline table */}
      <div className="glass-card rounded-2xl border border-border-light/40 overflow-hidden shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-border-light/40 bg-white/30 text-xs font-semibold text-graphite-light uppercase tracking-wider">
                <th className="py-4 px-6">Stage</th>
                <th className="py-4 px-6 text-center">Runtime</th>
                <th className="py-4 px-6 text-center">Input Jobs</th>
                <th className="py-4 px-6 text-center">Output Jobs</th>
                <th className="py-4 px-6 text-center">Rejected</th>
                <th className="py-4 px-6 text-center">Success Rate</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border-light/20 text-sm">
              {stages.map(stage => {
                const total = stage.input_jobs;
                const passed = stage.output_jobs;
                const rate = total > 0 ? Math.round((passed / total) * 100) : 100;
                
                return (
                  <tr key={stage.stage_name} className="hover:bg-white/40 transition-colors">
                    <td className="py-4 px-6 font-bold text-graphite">{stage.stage_name}</td>
                    <td className="py-4 px-6 text-center text-graphite-light font-mono font-semibold">{stage.execution_time_seconds.toFixed(1)}s</td>
                    <td className="py-4 px-6 text-center font-medium">{stage.input_jobs || "—"}</td>
                    <td className="py-4 px-6 text-center font-medium">{stage.output_jobs || "—"}</td>
                    <td className="py-4 px-6 text-center font-medium text-highlight">{stage.rejected_jobs || "—"}</td>
                    <td className="py-4 px-6 text-center">
                      <span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-bold ${
                        rate >= 90 ? "bg-emerald-100 text-emerald-700" :
                        rate >= 60 ? "bg-amber-100 text-amber-700" : "bg-rose-100 text-rose-700"
                      }`}>
                        {rate}%
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Heuristic recommendations panel */}
      {recommendations.length > 0 && (
        <div className="glass-card rounded-2xl p-6 border border-border-light/40">
          <h3 className="text-base font-bold text-graphite flex items-center gap-2 mb-4">
            <Cpu size={18} className="text-secondary" /> Intelligent Optimizer Recommendations
          </h3>
          <div className="flex flex-col gap-3">
            {recommendations.map((rec, i) => (
              <div key={i} className="flex gap-3 text-xs bg-white/40 p-4 rounded-xl border border-border-light/20 leading-relaxed text-graphite-light">
                <ShieldAlert size={16} className="text-secondary shrink-0" />
                <span>{rec}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
