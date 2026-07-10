"use client";

import { useEffect, useState } from "react";
import { Terminal, Clock, Play, CheckCircle2, RotateCw } from "lucide-react";

export default function AutomationFlow() {
  const [timeLeft, setTimeLeft] = useState("");

  useEffect(() => {
    const calculateTimeLeft = () => {
      const now = new Date();
      const nextRun = new Date();
      nextRun.setHours(7, 0, 0, 0); // 7:00 AM
      
      // If it's already past 7 AM, set next run for tomorrow
      if (now.getHours() >= 7) {
        nextRun.setDate(nextRun.getDate() + 1);
      }

      const diff = nextRun.getTime() - now.getTime();
      const hours = Math.floor(diff / (1000 * 60 * 60));
      const minutes = Math.floor((diff / (1000 * 60)) % 60);
      const seconds = Math.floor((diff / 1000) % 60);

      setTimeLeft(`${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`);
    };

    calculateTimeLeft();
    const interval = setInterval(calculateTimeLeft, 1000);
    return () => clearInterval(interval);
  }, []);

  const steps = [
    { title: "7:00 AM Trigger", desc: "Cron Scheduled Event", status: "completed" },
    { title: "Initialize Runner", desc: "Load venv & cache", status: "completed" },
    { title: "Candidate Profile", desc: "Parse candidate_profile.json", status: "completed" },
    { title: "Job Discovery", desc: "Autonomous API Crawler", status: "completed" },
    { title: "Confidence Scoring", desc: "Recruiter AI Evaluation", status: "completed" },
    { title: "Database Sync", desc: "Update Sheets & Notion CRM", status: "completed" },
    { title: "Email Dispatch", desc: "Send daily summaries", status: "completed" }
  ];

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
      {/* Timer & Cron status */}
      <div className="glass-card rounded-2xl p-6 border border-border-light/40 flex flex-col justify-between md:col-span-1">
        <div>
          <span className="text-xs font-bold uppercase tracking-wider text-graphite-light flex items-center gap-1.5">
            <Clock size={12} /> Next Daily Scheduled Run
          </span>
          <div className="text-5xl font-extrabold text-graphite tracking-tight mt-6 font-mono">
            {timeLeft}
          </div>
          <p className="text-xs text-graphite-light mt-3">
            Authoritative run executes autonomously every morning at 7:00 AM IST (1:30 AM UTC).
          </p>
        </div>

        <div className="mt-8 pt-4 border-t border-border-light/20 flex items-center gap-3">
          <div className="h-2 w-2 rounded-full bg-emerald-500 animate-ping" />
          <span className="text-xs font-bold text-emerald-600">Cron Scheduler Standby</span>
        </div>
      </div>

      {/* Visual Pipeline steps */}
      <div className="glass-card rounded-2xl p-6 border border-border-light/40 flex flex-col md:col-span-2">
        <h3 className="text-base font-bold text-graphite flex items-center gap-2 mb-6">
          <Terminal size={18} className="text-primary" /> Daily GitHub Actions Workflow Run
        </h3>

        <div className="flex flex-col gap-5 relative pl-6 border-l border-border-light/60">
          {steps.map((step, idx) => (
            <div key={step.title} className="relative">
              {/* Dot */}
              <div className="absolute -left-[31px] top-0.5 h-4.5 w-4.5 rounded-full bg-emerald-500 border-2 border-white flex items-center justify-center text-white">
                <CheckCircle2 size={12} className="stroke-[2.5]" />
              </div>
              
              <div className="flex flex-col text-left">
                <h4 className="font-bold text-sm text-graphite flex items-center gap-2">
                  {step.title}
                </h4>
                <span className="text-xs text-graphite-light mt-0.5">{step.desc}</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
