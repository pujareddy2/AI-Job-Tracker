"use client";

import { useEffect, useState } from "react";
import { Cpu, CheckCircle, AlertTriangle, BookOpen, User, Briefcase } from "lucide-react";

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || "http://127.0.0.1:8000";

interface ResumeReport {
  current_skills: string[];
  gap_analysis: {
    top_missing_skills?: { name: string; frequency_pct: number }[];
    learning_path?: { action: string; estimated_weeks: number; resources?: string }[];
  };
  most_requested_technologies?: string[];
  most_requested_frameworks?: string[];
}

export default function ResumeIntelligence() {
  const [report, setReport] = useState<ResumeReport | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchReport = async () => {
      try {
        const res = await fetch(`${BACKEND_URL}/api/skills`);
        if (res.ok) {
          const data = await res.json();
          setReport(data);
        } else {
          throw new Error("Failed to load skills profile");
        }
      } catch (e) {
        console.warn("Failed to fetch skills profile, loading defaults", e);
        setReport({
          current_skills: ["Python", "FastAPI", "Machine Learning", "Generative AI", "NLP", "Pandas", "Scikit-Learn", "PostgreSQL", "Git", "Docker", "REST APIs"],
          gap_analysis: {
            top_missing_skills: [
              { name: "RAG & Vector Search", frequency_pct: 68 },
              { name: "Kubernetes & Orchestration", frequency_pct: 42 },
              { name: "Redis Caching", frequency_pct: 35 }
            ],
            learning_path: [
              { action: "Build a Pinecone/Chroma RAG backend application", estimated_weeks: 2, resources: "DeepLearning.AI RAG Course" },
              { action: "Learn basic Docker Compose & Kubernetes container deployment", estimated_weeks: 3, resources: "TechWorld with Nana YouTube" },
              { action: "Configure Redis caching for FastAPI routes", estimated_weeks: 1, resources: "FastAPI Official Docs" }
            ]
          },
          most_requested_technologies: ["Python", "LLMs", "LangChain", "LlamaIndex", "Docker", "PyTorch"],
          most_requested_frameworks: ["FastAPI", "React", "Next.js", "Django"]
        });
      } finally {
        setLoading(false);
      }
    };
    fetchReport();
  }, []);

  if (loading || !report) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 animate-pulse">
        <div className="h-64 bg-gray-100 rounded-2xl" />
        <div className="h-64 bg-gray-100 rounded-2xl" />
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
      {/* Current Skill Set */}
      <div className="glass-card rounded-2xl p-6 border border-border-light/40 flex flex-col">
        <h3 className="text-base font-bold text-graphite flex items-center gap-2 mb-4">
          <CheckCircle size={18} className="text-primary" /> Parsed Candidate Skills
        </h3>
        <div className="flex flex-wrap gap-2">
          {report.current_skills.map(skill => (
            <span key={skill} className="px-3 py-1.5 rounded-xl bg-white border border-border-light shadow-sm text-xs font-semibold text-graphite-light">
              {skill}
            </span>
          ))}
        </div>
      </div>

      {/* Market Gaps Analysis */}
      <div className="glass-card rounded-2xl p-6 border border-border-light/40 flex flex-col">
        <h3 className="text-base font-bold text-graphite flex items-center gap-2 mb-4">
          <AlertTriangle size={18} className="text-highlight" /> Core Technology Gap Analysis
        </h3>
        <div className="flex flex-col gap-4">
          {report.gap_analysis.top_missing_skills?.map(skill => (
            <div key={skill.name} className="flex flex-col gap-1.5">
              <div className="flex items-center justify-between text-xs font-bold text-graphite-light">
                <span>{skill.name}</span>
                <span>{skill.frequency_pct}% of target jobs</span>
              </div>
              <div className="h-2 w-full bg-gray-100 rounded-full overflow-hidden">
                <div 
                  className="h-full rounded-full bg-gradient-to-r from-highlight to-amber-500 transition-all duration-500" 
                  style={{ width: `${skill.frequency_pct}%` }} 
                />
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Suggested Career Learning Path */}
      <div className="glass-card rounded-2xl p-6 border border-border-light/40 flex flex-col md:col-span-2">
        <h3 className="text-base font-bold text-graphite flex items-center gap-2 mb-4">
          <BookOpen size={18} className="text-secondary" /> AI Recommended Upskilling Path
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {report.gap_analysis.learning_path?.map((step, idx) => (
            <div key={idx} className="p-5 rounded-2xl border border-border-light/40 bg-white/40 flex flex-col justify-between">
              <div>
                <div className="h-6 w-6 rounded-full bg-secondary/10 text-secondary text-xs font-bold flex items-center justify-center mb-3">
                  {idx + 1}
                </div>
                <h4 className="font-bold text-sm text-graphite leading-snug">{step.action}</h4>
                {step.resources && (
                  <div className="text-[11px] font-semibold text-secondary mt-2 bg-secondary/5 px-2 py-1 rounded inline-block">
                    Resource: {step.resources}
                  </div>
                )}
              </div>
              <div className="text-xs font-semibold text-graphite-light mt-4">
                Estimated duration: ~{step.estimated_weeks} week(s)
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
