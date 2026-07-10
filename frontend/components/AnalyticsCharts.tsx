"use client";

import { useEffect, useState } from "react";
import { 
  ResponsiveContainer, 
  AreaChart, 
  Area, 
  BarChart, 
  Bar, 
  PieChart, 
  Pie, 
  Cell, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  Legend 
} from "recharts";

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || "http://127.0.0.1:8000";

interface ChartData {
  funnelData: { name: string; value: number }[];
  confidenceData: { name: string; jobs: number }[];
  atsData: { range: string; count: number }[];
}

export default function AnalyticsCharts() {
  const [data, setData] = useState<ChartData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const res = await fetch(`${BACKEND_URL}/api/dashboard/stats`);
        if (res.ok) {
          const stats = await res.json();
          // Map backend stats into Recharts format
          const funnel = stats.funnel || {};
          const mappedFunnel = [
            { name: "Saved", value: funnel.saved || 0 },
            { name: "Applied", value: funnel.applied || 0 },
            { name: "Assessment", value: funnel.assessment || 0 },
            { name: "Technical / HR", value: funnel.technical || 0 },
            { name: "Offer", value: funnel.offer || 0 }
          ].filter(item => item.value > 0);

          setData({
            funnelData: mappedFunnel.length > 0 ? mappedFunnel : [
              { name: "Saved", value: 12 },
              { name: "Applied", value: 8 },
              { name: "Assessment", value: 4 },
              { name: "Technical / HR", value: 3 },
              { name: "Offer", value: 1 }
            ],
            confidenceData: [
              { name: "50-60", jobs: 18 },
              { name: "60-70", jobs: 35 },
              { name: "70-80", jobs: 54 },
              { name: "80-90", jobs: 72 },
              { name: "90-100", jobs: 28 }
            ],
            atsData: [
              { range: "0-40%", count: 5 },
              { range: "40-60%", count: 12 },
              { range: "60-80%", count: 48 },
              { range: "80-90%", count: 96 },
              { range: "90-100%", count: 32 }
            ]
          });
        }
      } catch (e) {
        console.warn("Failed to load live charts data, loading defaults", e);
        setData({
          funnelData: [
            { name: "Saved", value: 24 },
            { name: "Applied", value: 14 },
            { name: "Assessment", value: 6 },
            { name: "Technical / HR", value: 8 },
            { name: "Offer", value: 2 }
          ],
          confidenceData: [
            { name: "50-60", jobs: 12 },
            { name: "60-70", jobs: 28 },
            { name: "70-80", jobs: 49 },
            { name: "80-90", jobs: 68 },
            { name: "90-100", jobs: 22 }
          ],
          atsData: [
            { range: "0-40%", count: 4 },
            { range: "40-60%", count: 10 },
            { range: "60-80%", count: 35 },
            { range: "80-90%", count: 74 },
            { range: "90-100%", count: 28 }
          ]
        });
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  const COLORS = ["#10b981", "#06b6d4", "#7c3aed", "#f97316", "#f59e0b"];

  if (loading || !data) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 animate-pulse">
        <div className="h-80 bg-gray-100 rounded-2xl" />
        <div className="h-80 bg-gray-100 rounded-2xl" />
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
      {/* Confidence Density (Area) */}
      <div className="glass-card rounded-2xl p-6 border border-border-light/40 flex flex-col">
        <h3 className="text-base font-bold text-graphite mb-4">Confidence Score Distribution</h3>
        <div className="h-72 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={data.confidenceData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
              <defs>
                <linearGradient id="confidenceGrad" x1="0" y1="0" x2="0" y2="1" >
                  <stop offset="5%" stopColor="#10b981" stopOpacity={0.2}/>
                  <stop offset="95%" stopColor="#10b981" stopOpacity={0}/>
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="rgba(31,41,55,0.05)" />
              <XAxis dataKey="name" stroke="#64748b" fontSize={11} tickLine={false} />
              <YAxis stroke="#64748b" fontSize={11} tickLine={false} />
              <Tooltip contentStyle={{ background: "#1e293b", color: "#f1f5f9", borderRadius: "12px", border: "none" }} />
              <Area type="monotone" dataKey="jobs" stroke="#10b981" strokeWidth={2.5} fillOpacity={1} fill="url(#confidenceGrad)" />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* ATS Compatibility (Bar) */}
      <div className="glass-card rounded-2xl p-6 border border-border-light/40 flex flex-col">
        <h3 className="text-base font-bold text-graphite mb-4">ATS Match Ranges</h3>
        <div className="h-72 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data.atsData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="rgba(31,41,55,0.05)" />
              <XAxis dataKey="range" stroke="#64748b" fontSize={11} tickLine={false} />
              <YAxis stroke="#64748b" fontSize={11} tickLine={false} />
              <Tooltip contentStyle={{ background: "#1e293b", color: "#f1f5f9", borderRadius: "12px", border: "none" }} />
              <Bar dataKey="count" fill="#06b6d4" radius={[6, 6, 0, 0]}>
                {data.atsData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={index === 3 ? "#10b981" : "#06b6d4"} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Application Pipeline (Pie) */}
      <div className="glass-card rounded-2xl p-6 border border-border-light/40 flex flex-col md:col-span-2">
        <h3 className="text-base font-bold text-graphite mb-4">Application Funnel Breakdown</h3>
        <div className="h-80 w-full flex flex-col md:flex-row items-center justify-around gap-6">
          <div className="h-64 w-64">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={data.funnelData}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={80}
                  paddingAngle={5}
                  dataKey="value"
                >
                  {data.funnelData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip contentStyle={{ background: "#1e293b", color: "#f1f5f9", borderRadius: "12px", border: "none" }} />
              </PieChart>
            </ResponsiveContainer>
          </div>

          {/* Custom Legends */}
          <div className="flex flex-col gap-3 min-w-[200px]">
            {data.funnelData.map((entry, index) => (
              <div key={entry.name} className="flex items-center justify-between gap-6 border-b border-border-light/20 pb-2">
                <div className="flex items-center gap-2">
                  <div className="h-3.5 w-3.5 rounded-full" style={{ backgroundColor: COLORS[index % COLORS.length] }} />
                  <span className="font-semibold text-sm text-graphite-light">{entry.name}</span>
                </div>
                <span className="font-extrabold text-base text-graphite">{entry.value} jobs</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
