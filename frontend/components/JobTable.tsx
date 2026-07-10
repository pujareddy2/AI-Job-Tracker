"use client";

import { useState, useEffect } from "react";
import { Search, MapPin, Layers, Award, Shield, ExternalLink, Calendar, ChevronLeft, ChevronRight, Check } from "lucide-react";

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || "http://127.0.0.1:8000";

interface Job {
  identity: {
    uuid: string;
    job_id: string;
  };
  company: {
    company_name: string;
    company_careers_url?: string;
  };
  job: {
    job_title: string;
    employment_type: string;
    experience_required: string;
    job_description?: string;
  };
  location: {
    location: string;
  };
  resume_match: {
    candidate_match_score: number;
    resume_keywords_matched?: string[];
    resume_keywords_missing?: string[];
  };
  ats_score?: number;
  confidence?: {
    overall_score: number;
    grade: string;
    category: string;
  };
  application: {
    application_url?: string;
  };
  metadata: {
    posted_date?: string;
  };
  application_status?: string;
}

export default function JobTable() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [locationFilter, setLocationFilter] = useState("");
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const limit = 10;

  const fetchJobs = async () => {
    setLoading(true);
    try {
      const query = new URLSearchParams({
        page: page.toString(),
        limit: limit.toString(),
      });
      if (search) query.append("q", search);
      if (statusFilter) query.append("status", statusFilter);
      if (locationFilter) query.append("location", locationFilter);

      const res = await fetch(`${BACKEND_URL}/api/jobs?${query.toString()}`);
      if (res.ok) {
        const data = await res.json();
        setJobs(data.jobs || []);
        setTotal(data.total || 0);
      } else {
        throw new Error("API call failed");
      }
    } catch (e) {
      console.warn("Failed to fetch live jobs, using premium mockup data", e);
      // Premium Mockup Jobs
      const mockJobs: Job[] = [
        {
          identity: { uuid: "job-1", job_id: "9d8456af" },
          company: { company_name: "Google AI" },
          job: { job_title: "Applied AI Engineer", employment_type: "Full-time", experience_required: "0-2 years" },
          location: { location: "Bangalore, India (Hybrid)" },
          resume_match: { candidate_match_score: 92 },
          ats_score: 88,
          confidence: { overall_score: 94, grade: "A+", category: "Strong Fit" },
          application: { application_url: "https://careers.google.com" },
          metadata: { posted_date: "1 day ago" },
          application_status: "Saved"
        },
        {
          identity: { uuid: "job-2", job_id: "ae0b1744" },
          company: { company_name: "NVIDIA" },
          job: { job_title: "GenAI Software Developer", employment_type: "Full-time", experience_required: "1-2 years" },
          location: { location: "Hyderabad, India" },
          resume_match: { candidate_match_score: 86 },
          ats_score: 81,
          confidence: { overall_score: 89, grade: "A", category: "Good Fit" },
          application: { application_url: "https://nvidia.wd5.myworkdayjobs.com" },
          metadata: { posted_date: "Today" },
          application_status: "Applied"
        },
        {
          identity: { uuid: "job-3", job_id: "5a44cdf1" },
          company: { company_name: "Stripe" },
          job: { job_title: "Backend AI Platform Engineer", employment_type: "Full-time", experience_required: "Entry Level" },
          location: { location: "Remote (India)" },
          resume_match: { candidate_match_score: 95 },
          ats_score: 90,
          confidence: { overall_score: 96, grade: "S", category: "Strong Fit" },
          application: { application_url: "https://stripe.com/jobs" },
          metadata: { posted_date: "2 days ago" },
          application_status: "Assessment"
        },
        {
          identity: { uuid: "job-4", job_id: "a1f96814" },
          company: { company_name: "OpenAI" },
          job: { job_title: "Conversational AI Developer", employment_type: "Full-time", experience_required: "0-1 years" },
          location: { location: "Bangalore, India" },
          resume_match: { candidate_match_score: 79 },
          ats_score: 74,
          confidence: { overall_score: 78, grade: "B", category: "Moderate Fit" },
          application: { application_url: "https://openai.com/careers" },
          metadata: { posted_date: "3 days ago" },
          application_status: "Saved"
        },
        {
          identity: { uuid: "job-5", job_id: "02ba5f94" },
          company: { company_name: "Microsoft Research" },
          job: { job_title: "ML Engineering Intern", employment_type: "Internship (Paid)", experience_required: "No graduation year" },
          location: { location: "Hyderabad, India" },
          resume_match: { candidate_match_score: 91 },
          ats_score: 87,
          confidence: { overall_score: 93, grade: "A+", category: "Strong Fit" },
          application: { application_url: "https://careers.microsoft.com" },
          metadata: { posted_date: "Today" },
          application_status: "HR Interview"
        }
      ];
      setJobs(mockJobs);
      setTotal(mockJobs.length);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchJobs();
  }, [page, search, statusFilter, locationFilter]);

  const updateStatus = async (uuid: string, newStatus: string) => {
    try {
      const res = await fetch(`${BACKEND_URL}/api/applications/status`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ job_uuid: uuid, status: newStatus }),
      });
      if (res.ok) {
        setJobs(prev => prev.map(j => j.identity.uuid === uuid ? { ...j, application_status: newStatus } : j));
      }
    } catch (e) {
      console.warn("Failed to update status on server, updating locally", e);
      setJobs(prev => prev.map(j => j.identity.uuid === uuid ? { ...j, application_status: newStatus } : j));
    }
  };

  const getStatusBadgeColor = (status: string) => {
    switch (status?.toLowerCase()) {
      case "applied": return "bg-blue-500/10 text-blue-500 border-blue-500/20";
      case "assessment": return "bg-orange-500/10 text-orange-500 border-orange-500/20";
      case "technical":
      case "hr interview": return "bg-purple-500/10 text-purple-500 border-purple-500/20";
      case "offer": return "bg-emerald-500/10 text-emerald-500 border-emerald-500/20";
      case "rejected":
      case "skip": return "bg-rose-500/10 text-rose-500 border-rose-500/20";
      default: return "bg-gray-500/10 text-gray-500 border-gray-500/20";
    }
  };

  return (
    <div className="flex flex-col gap-6">
      {/* Filters Bar */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {/* Search */}
        <div className="relative">
          <Search size={16} className="absolute left-3.5 top-1/2 transform -translate-y-1/2 text-graphite-light" />
          <input
            type="text"
            placeholder="Search role or company..."
            value={search}
            onChange={e => { setSearch(e.target.value); setPage(1); }}
            className="w-full pl-10 pr-4 py-2.5 rounded-xl border border-border-light/60 bg-white/60 focus:outline-none focus:border-primary/50 text-sm"
          />
        </div>

        {/* Location Filter */}
        <div className="relative">
          <MapPin size={16} className="absolute left-3.5 top-1/2 transform -translate-y-1/2 text-graphite-light" />
          <select
            value={locationFilter}
            onChange={e => { setLocationFilter(e.target.value); setPage(1); }}
            className="w-full pl-10 pr-4 py-2.5 rounded-xl border border-border-light/60 bg-white/60 focus:outline-none focus:border-primary/50 text-sm appearance-none"
          >
            <option value="">All Locations</option>
            <option value="bangalore">Bangalore</option>
            <option value="hyderabad">Hyderabad</option>
            <option value="remote">Remote</option>
          </select>
        </div>

        {/* Status Filter */}
        <div className="relative">
          <Layers size={16} className="absolute left-3.5 top-1/2 transform -translate-y-1/2 text-graphite-light" />
          <select
            value={statusFilter}
            onChange={e => { setStatusFilter(e.target.value); setPage(1); }}
            className="w-full pl-10 pr-4 py-2.5 rounded-xl border border-border-light/60 bg-white/60 focus:outline-none focus:border-primary/50 text-sm appearance-none"
          >
            <option value="">All Application Statuses</option>
            <option value="saved">Saved</option>
            <option value="applied">Applied</option>
            <option value="assessment">Assessment</option>
            <option value="hr interview">Interview</option>
            <option value="offer">Offer</option>
          </select>
        </div>
      </div>

      {/* Enterprise Job Grid/Table */}
      <div className="glass-card rounded-2xl border border-border-light/40 overflow-hidden shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-border-light/40 bg-white/30 text-xs font-semibold text-graphite-light uppercase tracking-wider">
                <th className="py-4 px-6">Role & Company</th>
                <th className="py-4 px-6">Location</th>
                <th className="py-4 px-6 text-center">Resume Match</th>
                <th className="py-4 px-6 text-center">ATS Score</th>
                <th className="py-4 px-6 text-center">Confidence</th>
                <th className="py-4 px-6">Status</th>
                <th className="py-4 px-6 text-center">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border-light/20 text-sm">
              {loading ? (
                // Skeletons
                Array.from({ length: 4 }).map((_, idx) => (
                  <tr key={idx} className="animate-pulse">
                    <td className="py-5 px-6">
                      <div className="h-4 w-32 bg-gray-200 rounded mb-2" />
                      <div className="h-3 w-20 bg-gray-100 rounded" />
                    </td>
                    <td className="py-5 px-6"><div className="h-4 w-24 bg-gray-100 rounded" /></td>
                    <td className="py-5 px-6"><div className="h-6 w-12 bg-gray-100 rounded mx-auto" /></td>
                    <td className="py-5 px-6"><div className="h-6 w-12 bg-gray-100 rounded mx-auto" /></td>
                    <td className="py-5 px-6"><div className="h-6 w-16 bg-gray-100 rounded mx-auto" /></td>
                    <td className="py-5 px-6"><div className="h-6 w-20 bg-gray-100 rounded" /></td>
                    <td className="py-5 px-6"><div className="h-9 w-20 bg-gray-100 rounded mx-auto" /></td>
                  </tr>
                ))
              ) : jobs.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-12 text-center text-graphite-light font-medium">
                    No jobs matching current criteria found.
                  </td>
                </tr>
              ) : (
                jobs.map(job => (
                  <tr key={job.identity.uuid} className="hover:bg-white/40 transition-colors">
                    {/* Role & Company */}
                    <td className="py-5 px-6">
                      <div className="font-bold text-graphite text-base">{job.job.job_title}</div>
                      <div className="text-xs text-graphite-light mt-0.5 font-medium flex items-center gap-1.5">
                        <span>{job.company.company_name}</span>
                        <span className="h-1.5 w-1.5 rounded-full bg-border-light" />
                        <span>{job.job.experience_required}</span>
                      </div>
                    </td>

                    {/* Location */}
                    <td className="py-5 px-6 font-medium text-graphite-light">
                      {job.location.location}
                    </td>

                    {/* Resume Match */}
                    <td className="py-5 px-6 text-center">
                      <span className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-bold ${
                        job.resume_match.candidate_match_score >= 85 ? "bg-emerald-100 text-emerald-700" :
                        job.resume_match.candidate_match_score >= 70 ? "bg-amber-100 text-amber-700" : "bg-red-100 text-red-700"
                      }`}>
                        <Award size={12} /> {job.resume_match.candidate_match_score}%
                      </span>
                    </td>

                    {/* ATS Score */}
                    <td className="py-5 px-6 text-center font-bold text-graphite">
                      {job.ats_score ? `${job.ats_score}%` : "—"}
                    </td>

                    {/* Confidence score */}
                    <td className="py-5 px-6 text-center">
                      {job.confidence ? (
                        <div className="flex flex-col items-center">
                          <span className="font-extrabold text-graphite text-base">{job.confidence.overall_score}</span>
                          <span className="text-[10px] uppercase font-bold tracking-wider text-primary">{job.confidence.category}</span>
                        </div>
                      ) : "—"}
                    </td>

                    {/* Status Dropdown */}
                    <td className="py-5 px-6">
                      <select
                        value={job.application_status || "Saved"}
                        onChange={e => updateStatus(job.identity.uuid, e.target.value)}
                        className={`px-3 py-1.5 rounded-xl border text-xs font-bold focus:outline-none appearance-none cursor-pointer ${getStatusBadgeColor(job.application_status || "Saved")}`}
                      >
                        <option value="Saved">Saved</option>
                        <option value="Applied">Applied</option>
                        <option value="Assessment">Assessment</option>
                        <option value="HR Interview">Interview</option>
                        <option value="Offer">Offer</option>
                        <option value="Rejected">Rejected</option>
                      </select>
                    </td>

                    {/* Action apply button */}
                    <td className="py-5 px-6 text-center">
                      {job.application.application_url ? (
                        <a
                          href={job.application.application_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-white border border-border-light hover:border-primary/40 hover:bg-softwhite text-xs font-bold text-graphite transition-all"
                        >
                          Apply <ExternalLink size={12} />
                        </a>
                      ) : "—"}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination footer */}
        <div className="border-t border-border-light/20 bg-white/20 px-6 py-4 flex items-center justify-between">
          <div className="text-xs text-graphite-light font-medium">
            Showing <span className="font-bold text-graphite">{jobs.length}</span> of <span className="font-bold text-graphite">{total}</span> opportunities
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => setPage(prev => Math.max(1, prev - 1))}
              disabled={page === 1}
              className="p-2 rounded-xl border border-border-light/40 bg-white hover:bg-softwhite disabled:opacity-50 text-graphite transition-all"
            >
              <ChevronLeft size={16} />
            </button>
            <button
              onClick={() => setPage(prev => (prev * limit < total ? prev + 1 : prev))}
              disabled={page * limit >= total}
              className="p-2 rounded-xl border border-border-light/40 bg-white hover:bg-softwhite disabled:opacity-50 text-graphite transition-all"
            >
              <ChevronRight size={16} />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
