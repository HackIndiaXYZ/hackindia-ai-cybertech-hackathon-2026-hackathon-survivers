"use client";

import dynamic from "next/dynamic";
import { useEffect, useMemo, useState } from "react";
import {
  Activity, ArrowRight, Bell, CheckCircle2, Clock3,
  FileText, LayoutDashboard, Lightbulb, MapPin, Menu, Plus, Search,
  Settings, ShieldCheck, Sparkles, Users, Waves, X, Droplets,
  Construction, Trash2, ChartNoAxesCombined, Send,
} from "lucide-react";
import {
  Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import {
  analyzeComplaintWithAgents, analyzeIssueImage, createComplaint, getComplaints,
  type DashboardComplaint,
} from "@/lib/api";

const MapView = dynamic(() => import("@/components/map-view"), {
  ssr: false,
  loading: () => <div className="flex h-[460px] items-center justify-center rounded-2xl bg-violet-50 text-sm text-violet-700">Loading interactive map…</div>,
});

type Complaint = DashboardComplaint;

type AgentAnalysis = {
  category?: string;
  severity?: string;
  confidence?: number;
  summary?: string;
  reasoning?: string;
  requires_human_review?: boolean;
};

type AgentResult = {
  analysis?: AgentAnalysis;
  civic_guidance?: unknown[];
  error?: string | null;
  review?: unknown;
};

type ImageAnalysisResult = {
  ok?: boolean;
  message?: string;
  issue_count?: number;
  [key: string]: unknown;
};


const chart = [
  { day: "Mon", reports: 42, resolved: 28 },
  { day: "Tue", reports: 58, resolved: 35 },
  { day: "Wed", reports: 49, resolved: 39 },
  { day: "Thu", reports: 73, resolved: 46 },
  { day: "Fri", reports: 64, resolved: 51 },
  { day: "Sat", reports: 88, resolved: 59 },
  { day: "Sun", reports: 69, resolved: 62 },
];

const nav = [
  { label: "Overview", icon: LayoutDashboard },
  { label: "Complaints", icon: FileText },
  { label: "Live map", icon: MapPin },
  { label: "AI agents", icon: Sparkles },
  { label: "Departments", icon: Users },
  { label: "Analytics", icon: ChartNoAxesCombined },
];

const categories = [
  { name: "Pothole", icon: Construction, color: "bg-rose-100 text-rose-600" },
  { name: "Garbage", icon: Trash2, color: "bg-amber-100 text-amber-600" },
  { name: "Streetlight", icon: Lightbulb, color: "bg-violet-100 text-violet-600" },
  { name: "Water leakage", icon: Droplets, color: "bg-sky-100 text-sky-600" },
  { name: "Drainage", icon: Waves, color: "bg-emerald-100 text-emerald-600" },
];

const stages = [
  { name: "Classification Agent", detail: "Identify issue type and evidence", color: "bg-violet-500" },
  { name: "Verification Agent", detail: "Check evidence and possible duplicates", color: "bg-blue-500" },
  { name: "Priority Agent", detail: "Assess urgency and safety impact", color: "bg-rose-500" },
  { name: "Routing Agent", detail: "Choose responsible department", color: "bg-amber-500" },
  { name: "Resolution Agent", detail: "Review repair evidence", color: "bg-emerald-500" },
];

function Badge({ value }: { value: string }) {
  const colors: Record<string, string> = {
    Critical: "bg-rose-100 text-rose-700",
    High: "bg-orange-100 text-orange-700",
    Medium: "bg-amber-100 text-amber-800",
    Low: "bg-slate-100 text-slate-600",
    Submitted: "bg-sky-100 text-sky-700",
    "Under review": "bg-violet-100 text-violet-700",
    Assigned: "bg-blue-100 text-blue-700",
    "In progress": "bg-amber-100 text-amber-800",
    Resolved: "bg-emerald-100 text-emerald-700",
  };
  return <span className={`inline-flex rounded-full px-2.5 py-1 text-[11px] font-bold ${colors[value] || "bg-slate-100 text-slate-600"}`}>{value}</span>;
}

export default function Home() {
  const [page, setPage] = useState("Overview");
  const [complaints, setComplaints] = useState<Complaint[]>([]);
  const [loadingComplaints, setLoadingComplaints] = useState(true);
  const [apiError, setApiError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [latitude, setLatitude] = useState("");
  const [longitude, setLongitude] = useState("");
  const [locationMessage, setLocationMessage] = useState("");
  const [agentText, setAgentText] = useState("");
  const [agentResult, setAgentResult] = useState<AgentResult | null>(null);
  const [agentError, setAgentError] = useState("");
  const [agentLoading, setAgentLoading] = useState(false);
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [imageResult, setImageResult] = useState<ImageAnalysisResult | null>(null);
  const [imageLoading, setImageLoading] = useState(false);
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("All");
  const [priority, setPriority] = useState("All");
  const [showForm, setShowForm] = useState(false);
  const [mobile, setMobile] = useState(false);
  const [theme, setTheme] = useState("Vibrant");
  const [notice, setNotice] = useState("");
  const [selected, setSelected] = useState<Complaint | null>(null);
  const [form, setForm] = useState({ title: "", category: "Pothole", location: "", description: "" });

  async function refreshComplaints() {
    setLoadingComplaints(true);
    setApiError("");
    try {
      const records = await getComplaints();
      setComplaints(records);
    } catch (error) {
      setApiError(error instanceof Error ? error.message : "Could not load complaints.");
    } finally {
      setLoadingComplaints(false);
    }
  }

  useEffect(() => {
    const timer = window.setTimeout(() => { void refreshComplaints(); }, 0);
    return () => window.clearTimeout(timer);
  }, []);

  function useCurrentLocation() {
    if (!navigator.geolocation) {
      setLocationMessage("Geolocation is not available in this browser. Enter coordinates manually.");
      return;
    }
    setLocationMessage("Requesting location permission…");
    navigator.geolocation.getCurrentPosition(
      (position) => {
        setLatitude(position.coords.latitude.toFixed(6));
        setLongitude(position.coords.longitude.toFixed(6));
        setLocationMessage("Coordinates captured from your browser.");
      },
      (error) => {
        setLocationMessage(error.message || "Location permission was not granted. Enter coordinates manually.");
      },
      { enableHighAccuracy: true, timeout: 12000, maximumAge: 60000 }
    );
  }

  async function runAgentAnalysis() {
    if (agentText.trim().length < 1) {
      setAgentError("Describe the civic issue first.");
      return;
    }
    setAgentLoading(true);
    setAgentError("");
    setAgentResult(null);
    try {
      const result = await analyzeComplaintWithAgents(agentText.trim());
      setAgentResult(result);
    } catch (error) {
      setAgentError(error instanceof Error ? error.message : "AI-agent request failed.");
    } finally {
      setAgentLoading(false);
    }
  }

  async function runImageAnalysis() {
    if (!imageFile) {
      notify("Choose an image first.");
      return;
    }
    setImageLoading(true);
    setImageResult(null);
    try {
      const result = await analyzeIssueImage(imageFile);
      setImageResult(result);
    } catch (error) {
      setImageResult({
        ok: false,
        message: error instanceof Error ? error.message : "Image analysis failed.",
      });
    } finally {
      setImageLoading(false);
    }
  }


  const filtered = useMemo(() => complaints.filter((c) =>
    `${c.id} ${c.title} ${c.location} ${c.category}`.toLowerCase().includes(query.toLowerCase()) &&
    (status === "All" || c.status === status) &&
    (priority === "All" || c.priority === priority)
  ), [complaints, query, status, priority]);

  function notify(message: string) {
    setNotice(message);
    window.setTimeout(() => setNotice(""), 3200);
  }

  async function submitComplaint(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const lat = Number(latitude);
    const lon = Number(longitude);
    if (!latitude.trim() || !longitude.trim() ||
        !Number.isFinite(lat) || !Number.isFinite(lon) ||
        lat < -90 || lat > 90 || lon < -180 || lon > 180) {
      notify("Enter valid latitude and longitude, or use your current location.");
      return;
    }

    const categoryMap: Record<string, string> = {
      "Pothole": "pothole",
      "Garbage": "garbage",
      "Streetlight": "streetlight",
      "Water leakage": "water_leakage",
      "Drainage": "drainage",
    };
    const description = [
      form.title.trim(),
      form.description.trim(),
      form.location.trim() ? `Reported location: ${form.location.trim()}` : "",
    ].filter(Boolean).join("\\n");

    setSubmitting(true);
    try {
      const created = await createComplaint({
        category: categoryMap[form.category] || "pothole",
        description,
        latitude: lat,
        longitude: lon,
      });
      setComplaints((old) => [created, ...old.filter((c) => c.id !== created.id)]);
      setForm({ title: "", category: "Pothole", location: "", description: "" });
      setLatitude("");
      setLongitude("");
      setLocationMessage("");
      setShowForm(false);
      setPage("Complaints");
      notify(`Complaint submitted successfully: ${created.id}`);
      void refreshComplaints();
    } catch (error) {
      notify(error instanceof Error ? `Submission failed: ${error.message}` : "Complaint submission failed.");
    } finally {
      setSubmitting(false);
    }
  }

  const vibrant = theme === "Vibrant";
  const accent = vibrant ? "from-violet-600 via-fuchsia-500 to-orange-400" : "from-slate-700 via-slate-600 to-slate-500";

  return (
    <main className={`min-h-screen bg-gradient-to-br ${vibrant ? "from-violet-50 via-white to-orange-50" : "from-slate-100 via-white to-slate-100"} text-slate-800`}>
      <aside className={`fixed inset-y-0 left-0 z-40 flex w-[250px] flex-col bg-[#17152e] text-white shadow-2xl shadow-violet-950/20 transition-transform lg:translate-x-0 ${mobile ? "translate-x-0" : "-translate-x-full"}`}>
        <div className="flex h-[82px] items-center gap-3 border-b border-white/10 px-5">
          <div className={`flex h-11 w-11 items-center justify-center rounded-2xl bg-gradient-to-br ${accent} shadow-lg`}><MapPin size={23}/></div>
          <div><div className="text-lg font-black tracking-tight">FixMyCity<span className="text-orange-300">.</span></div><div className="text-[10px] font-bold uppercase tracking-[.2em] text-violet-200">Civic intelligence</div></div>
          <button onClick={() => setMobile(false)} className="ml-auto lg:hidden" aria-label="Close menu"><X size={18}/></button>
        </div>
        <div className="px-4 pt-7 text-[10px] font-bold uppercase tracking-[.2em] text-violet-300">Workspace</div>
        <nav className="space-y-1 px-3 pt-3">
          {nav.map(({ label, icon: Icon }, i) => <button key={label} onClick={() => { setPage(label); setMobile(false); }} className={`flex w-full items-center gap-3 rounded-xl px-3 py-3 text-left text-sm transition ${page === label ? "bg-gradient-to-r from-violet-600 to-fuchsia-600 font-bold text-white shadow-lg shadow-violet-950/30" : "text-violet-100/70 hover:bg-white/10 hover:text-white"}`}><Icon size={18}/><span className="flex-1">{label}</span>{i === 1 && <span className="rounded-md bg-orange-400 px-2 py-0.5 text-[10px] font-black text-white">{complaints.length}</span>}</button>)}
        </nav>
        <div className="px-4 pt-8 text-[10px] font-bold uppercase tracking-[.2em] text-violet-300">Preferences</div>
        <div className="space-y-2 px-3 pt-3">
          <button onClick={() => setPage("Settings")} className={`flex w-full items-center gap-3 rounded-xl px-3 py-3 text-sm ${page === "Settings" ? "bg-white/10 text-white" : "text-violet-100/70 hover:bg-white/10"}`}><Settings size={18}/> Settings</button>
          <div className="rounded-2xl border border-white/10 bg-white/[.06] p-4">
            <div className="flex items-center gap-2 text-xs font-bold"><span className="h-2 w-2 animate-pulse rounded-full bg-emerald-400"/><ShieldCheck size={16} className="text-emerald-300"/> Frontend status</div>
            <p className="mt-2 text-[11px] leading-5 text-violet-100/60">Interactive preview · sample data only</p>
          </div>
        </div>
        <div className="mt-auto border-t border-white/10 p-4"><div className="flex items-center gap-3"><div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-orange-300 to-pink-400 font-black text-violet-950">FM</div><div><div className="text-xs font-bold">City operations</div><div className="mt-1 text-[10px] text-violet-200/60">Demo administrator</div></div></div></div>
      </aside>

      {mobile && <button aria-label="Close navigation" onClick={() => setMobile(false)} className="fixed inset-0 z-30 bg-black/40 lg:hidden"/>}

      <section className="min-h-screen lg:pl-[250px]">
        <header className="sticky top-0 z-20 flex h-[72px] items-center justify-between border-b border-violet-100 bg-white/85 px-4 backdrop-blur-xl sm:px-7">
          <div className="flex items-center gap-3"><button onClick={() => setMobile(true)} className="rounded-xl border border-slate-200 p-2 lg:hidden" aria-label="Open menu"><Menu size={19}/></button><div><div className="text-[10px] font-bold uppercase tracking-[.15em] text-violet-500">Workspace / {page}</div><div className="mt-1 text-sm font-extrabold">Civic operations center</div></div></div>
          <div className="flex items-center gap-2"><span className="hidden rounded-full bg-emerald-50 px-3 py-2 text-[11px] font-bold text-emerald-700 sm:inline-flex"><span className="mr-2 mt-1 h-2 w-2 rounded-full bg-emerald-500"/>{apiError ? "API unavailable" : loadingComplaints ? "Connecting to API…" : "Backend connected"}</span><button onClick={() => notify("You are viewing the local demo. Notifications are not connected.")} className="relative rounded-xl border border-slate-200 p-2.5 hover:bg-violet-50" aria-label="Notifications"><Bell size={17}/><span className="absolute right-2 top-2 h-2 w-2 rounded-full bg-rose-500"/></button><button onClick={() => setPage("Settings")} className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-violet-500 to-pink-500 text-xs font-black text-white">CO</button></div>
        </header>

        <div className="mx-auto max-w-[1600px] px-4 py-6 sm:px-7 xl:px-9">
          <div className="mb-7 flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
            <div><div className="mb-2 inline-flex items-center gap-2 rounded-full bg-violet-100 px-3 py-1 text-[10px] font-black uppercase tracking-[.12em] text-violet-700"><Sparkles size={13}/> FixMyCity intelligence <span className="rounded-full bg-orange-200 px-2 py-0.5 text-orange-800">Demo</span></div><h1 className="text-3xl font-black tracking-tight sm:text-4xl">{page === "Overview" ? "City at a glance" : page}<span className="text-fuchsia-500">.</span></h1><p className="mt-2 max-w-2xl text-sm text-slate-500">{page === "Overview" ? "Turn civic problems into visible progress. Every report is a step toward a better city." : page === "Live map" ? "Explore issue locations and click a marker to inspect its report." : page === "AI agents" ? "Inspect the workflow that understands, verifies, prioritizes, and routes civic issues." : page === "Complaints" ? "Search, filter, and inspect the current complaint queue." : `Explore ${page.toLowerCase()} in the FixMyCity workspace.`}</p></div>
            <button onClick={() => setShowForm(true)} className={`inline-flex items-center justify-center gap-2 rounded-xl bg-gradient-to-r ${accent} px-5 py-3 text-sm font-bold text-white shadow-lg shadow-violet-300/40 transition hover:-translate-y-0.5`}><Plus size={17}/> Report an issue <ArrowRight size={15}/></button>
          </div>

          {page === "Settings" && <section className="mb-6 rounded-2xl border border-violet-100 bg-white p-6 shadow-sm"><h2 className="text-lg font-black">Appearance settings</h2><p className="mt-1 text-sm text-slate-500">Change the accent palette for this preview.</p><div className="mt-5 flex flex-wrap gap-3">{["Vibrant","Classic"].map((t)=><button key={t} onClick={()=>setTheme(t)} className={`rounded-xl border px-5 py-3 text-sm font-bold ${theme===t?"border-violet-500 bg-violet-50 text-violet-700":"border-slate-200 hover:bg-slate-50"}`}>{t}{theme===t?" ✓":""}</button>)}</div><p className="mt-4 text-xs text-slate-400">Theme choice applies immediately; persistence can be added later.</p></section>}

          {page === "Live map" && <section className="mb-6 rounded-2xl border border-violet-100 bg-white p-4 shadow-sm sm:p-6"><div className="mb-4 flex flex-wrap items-center justify-between gap-3"><div><h2 className="font-black">Civic issue map</h2><p className="mt-1 text-xs text-slate-500">Interactive OpenStreetMap · locations from backend complaint records</p></div><button onClick={()=>notify("Markers use coordinates saved with backend complaints.")} className="rounded-lg bg-violet-100 px-3 py-2 text-xs font-bold text-violet-700">About these markers</button></div><MapView complaints={complaints} /></section>}

          {page === "AI agents" && <section className="mb-6 space-y-5">
            <div className="rounded-2xl border border-violet-100 bg-white p-5 shadow-sm sm:p-7">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div><h2 className="text-xl font-black">Live civic analysis</h2><p className="mt-1 text-sm text-slate-500">Calls the existing AI-agent API. Analysis is advisory and may require human review.</p></div>
                <span className="rounded-full bg-violet-100 px-3 py-1.5 text-xs font-bold text-violet-700">Connected workflow</span>
              </div>
              <label className="mt-5 block text-xs font-bold">Describe the civic issue
                <textarea value={agentText} onChange={e=>setAgentText(e.target.value)} rows={4} maxLength={5000} placeholder="Example: An uncovered drain beside a school is causing a safety risk…" className="mt-2 w-full rounded-xl border border-slate-200 p-3 text-sm outline-none focus:border-violet-400"/>
              </label>
              <button disabled={agentLoading || !agentText.trim()} onClick={()=>void runAgentAnalysis()} className="mt-3 inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-violet-600 to-fuchsia-500 px-5 py-3 text-sm font-bold text-white disabled:opacity-50"><Sparkles size={16}/>{agentLoading?"Analyzing…":"Analyze with AI agents"}</button>
              {agentError && <p role="alert" className="mt-3 rounded-xl bg-rose-50 p-3 text-sm text-rose-700">{agentError}</p>}
              {agentResult && <div className="mt-5 rounded-2xl border border-violet-100 bg-violet-50/60 p-4">
                {agentResult.analysis ? <><h3 className="font-black">Analysis result</h3><div className="mt-3 grid gap-3 sm:grid-cols-3">
                  <div className="rounded-xl bg-white p-3"><div className="text-xs text-slate-500">Category</div><div className="mt-1 font-bold">{agentResult.analysis.category || "Not provided"}</div></div>
                  <div className="rounded-xl bg-white p-3"><div className="text-xs text-slate-500">Severity</div><div className="mt-1 font-bold">{agentResult.analysis.severity || "Not provided"}</div></div>
                  <div className="rounded-xl bg-white p-3"><div className="text-xs text-slate-500">Confidence</div><div className="mt-1 font-bold">{typeof agentResult.analysis.confidence === "number" ? `${(agentResult.analysis.confidence * 100).toFixed(1)}%` : "Not provided"}</div></div>
                </div><p className="mt-3 text-sm"><strong>Summary:</strong> {agentResult.analysis.summary || "No summary returned."}</p><p className="mt-2 text-sm"><strong>Reasoning:</strong> {agentResult.analysis.reasoning || "No reasoning returned."}</p><p className="mt-2 text-sm"><strong>Human review:</strong> {agentResult.analysis.requires_human_review ? "Required" : "Not flagged by the workflow"}</p>
                {Array.isArray(agentResult.civic_guidance) && agentResult.civic_guidance.length > 0 && <div className="mt-4"><h4 className="font-bold">Civic guidance</h4><ul className="mt-2 list-disc space-y-1 pl-5 text-sm">{agentResult.civic_guidance.map((g: unknown, i: number)=><li key={i}>{typeof g === "string" ? g : JSON.stringify(g)}</li>)}</ul></div>}
                </> : <pre className="overflow-auto whitespace-pre-wrap text-xs">{JSON.stringify(agentResult, null, 2)}</pre>}
              </div>}
            </div>
            <div className="rounded-2xl border border-violet-100 bg-white p-5 shadow-sm sm:p-7">
              <h2 className="text-xl font-black">Computer vision image analysis</h2>
              <p className="mt-1 text-sm text-slate-500">Uses the existing backend ML endpoint. Detection is preliminary evidence, not confirmation that a complaint is valid.</p>
              <input type="file" accept="image/jpeg,image/png,image/webp" onChange={e=>{setImageFile(e.target.files?.[0] || null);setImageResult(null);}} className="mt-4 block w-full text-sm"/>
              <button disabled={!imageFile || imageLoading} onClick={()=>void runImageAnalysis()} className="mt-3 rounded-xl bg-slate-900 px-5 py-3 text-sm font-bold text-white disabled:opacity-50">{imageLoading?"Analyzing image…":"Analyze image"}</button>
              {imageResult && <div className={`mt-4 rounded-xl p-4 text-sm ${imageResult.ok ? "bg-emerald-50 text-emerald-900" : "bg-rose-50 text-rose-800"}`}><div className="font-bold">{imageResult.ok ? "Image analysis completed" : "Image analysis could not complete"}</div><p className="mt-1">{(typeof imageResult.message === "string" ? imageResult.message : (imageResult.ok ? `${imageResult.issue_count ?? 0} issue(s) detected.` : "Check the backend service and model setup."))}</p><pre className="mt-3 max-h-64 overflow-auto whitespace-pre-wrap text-xs">{JSON.stringify(imageResult, null, 2)}</pre></div>}
            </div>
          </section>}

          {page === "Overview" && <div className="mb-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">{[
            {label:"Total complaints",value:String(complaints.length),sub:loadingComplaints?"Loading records":"Records returned by backend",icon:FileText,gradient:"from-violet-500 to-indigo-500",pale:"bg-violet-50",ink:"text-violet-600"},
            {label:"Awaiting action",value:String(complaints.filter(c=>["Submitted","Under review","Assigned","In progress"].includes(c.status)).length),sub:"Open reports in loaded records",icon:Clock3,gradient:"from-orange-400 to-rose-500",pale:"bg-orange-50",ink:"text-orange-600"},
            {label:"Resolved this week",value:String(complaints.filter(c=>c.status==="Resolved").length),sub:"Resolved in loaded records",icon:CheckCircle2,gradient:"from-emerald-400 to-teal-500",pale:"bg-emerald-50",ink:"text-emerald-600"},
            {label:"SLA compliance",value:"—",sub:"SLA metric not yet aggregated",icon:Activity,gradient:"from-sky-400 to-blue-600",pale:"bg-sky-50",ink:"text-sky-600"},
          ].map((k,i)=><div key={k.label} className="relative overflow-hidden rounded-2xl border border-white bg-white p-5 shadow-sm transition hover:-translate-y-1 hover:shadow-xl hover:shadow-violet-100/60"><div className={`absolute inset-x-0 top-0 h-1 bg-gradient-to-r ${k.gradient}`}/><div className="flex items-center justify-between"><span className="text-xs font-semibold text-slate-500">{k.label}</span><span className={`flex h-10 w-10 items-center justify-center rounded-2xl ${k.pale} ${k.ink}`}><k.icon size={19}/></span></div><div className="mt-4 text-3xl font-black tracking-tight">{k.value}</div><div className={`mt-2 text-[11px] font-medium ${k.ink}`}>{k.sub}</div><div className={`mt-4 h-1.5 overflow-hidden rounded-full ${k.pale}`}><div className={`h-full rounded-full bg-gradient-to-r ${k.gradient}`} style={{ width: `${complaints.length ? Math.min(100, ([complaints.length, complaints.filter(c => ["Submitted", "Under review", "Assigned", "In progress"].includes(c.status)).length, complaints.filter(c => c.status === "Resolved").length, 0][i] / complaints.length) * 100) : 0}%` }}/></div></div>)}</div>}

          {(page === "Overview" || page === "Analytics") && <div className="mb-6 grid gap-5 xl:grid-cols-[1.6fr_1fr]"><section className="rounded-2xl border border-violet-100 bg-white p-5 shadow-sm sm:p-6"><div className="mb-5 flex flex-wrap items-center justify-between gap-2"><div><h2 className="font-black">Reports & resolution trends</h2><p className="mt-1 text-xs text-slate-500">Illustrative weekly data</p></div><span className="rounded-full bg-violet-100 px-3 py-1.5 text-[10px] font-bold text-violet-700">Last 7 days</span></div><div className="h-[260px]"><ResponsiveContainer width="100%" height="100%"><AreaChart data={chart} margin={{top:8,right:8,left:-20,bottom:0}}><defs><linearGradient id="reports" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#8b5cf6" stopOpacity={.3}/><stop offset="100%" stopColor="#8b5cf6" stopOpacity={0}/></linearGradient><linearGradient id="resolved" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#fb7185" stopOpacity={.2}/><stop offset="100%" stopColor="#fb7185" stopOpacity={0}/></linearGradient></defs><CartesianGrid stroke="#f1f0f9" strokeDasharray="4 4" vertical={false}/><XAxis dataKey="day" axisLine={false} tickLine={false} tick={{fontSize:11,fill:"#94a3b8"}}/><YAxis axisLine={false} tickLine={false} tick={{fontSize:11,fill:"#94a3b8"}}/><Tooltip contentStyle={{borderRadius:12,border:"1px solid #ede9fe",fontSize:12}}/><Area type="monotone" dataKey="reports" name="Reports" stroke="#8b5cf6" strokeWidth={3} fill="url(#reports)"/><Area type="monotone" dataKey="resolved" name="Resolved" stroke="#fb7185" strokeWidth={3} fill="url(#resolved)"/></AreaChart></ResponsiveContainer></div><div className="mt-3 flex gap-5 text-xs"><span className="flex items-center gap-2"><span className="h-2.5 w-2.5 rounded-full bg-violet-500"/>Reports</span><span className="flex items-center gap-2"><span className="h-2.5 w-2.5 rounded-full bg-rose-400"/>Resolved</span></div></section><section className="rounded-2xl bg-gradient-to-br from-violet-700 via-purple-600 to-fuchsia-600 p-6 text-white shadow-lg shadow-violet-200"><div className="flex items-center gap-2 text-xs font-bold text-violet-100"><Sparkles size={16}/> AI OPERATIONS</div><h2 className="mt-4 text-2xl font-black">From report to resolution</h2><p className="mt-2 text-sm leading-6 text-white/75">Specialized agents can help classify, verify, prioritize, and route each civic issue.</p><div className="mt-6 space-y-3">{stages.slice(0,4).map((s,i)=><div key={s.name} className="flex items-center gap-3 rounded-xl border border-white/15 bg-white/10 p-3"><span className="flex h-7 w-7 items-center justify-center rounded-lg bg-white/15 text-xs font-black">{i+1}</span><span className="flex-1 text-xs font-bold">{s.name}</span><span className="text-[10px] text-white/70">Preview</span></div>)}</div><button onClick={()=>setPage("AI agents")} className="mt-5 flex w-full items-center justify-center gap-2 rounded-xl bg-white py-3 text-xs font-black text-violet-700 hover:bg-orange-50">Explore AI workflow <ArrowRight size={14}/></button></section></div>}

          {(page === "Overview" || page === "Live map") && page === "Overview" && <section className="mb-6 rounded-2xl border border-violet-100 bg-white p-5 shadow-sm sm:p-6"><div className="mb-4 flex flex-wrap items-center justify-between gap-3"><div><h2 className="font-black">Issue hotspots</h2><p className="mt-1 text-xs text-slate-500">Explore coordinates attached to saved complaints</p></div><button onClick={()=>setPage("Live map")} className="rounded-xl bg-violet-100 px-4 py-2.5 text-xs font-bold text-violet-700 hover:bg-violet-200">Open full map →</button></div><MapView complaints={complaints} /></section>}

          {(page === "Overview" || page === "Complaints" || page === "Departments") && <section className="mb-6 overflow-hidden rounded-2xl border border-violet-100 bg-white shadow-sm"><div className="flex flex-col justify-between gap-4 border-b border-violet-50 p-5 sm:flex-row sm:items-center"><div><h2 className="font-black">{page === "Departments" ? "Department assignments" : "Complaint explorer"}</h2><p className="mt-1 text-xs text-slate-500">Search, filter, and open a report to inspect it</p></div><div className="flex flex-wrap gap-2"><div className="relative"><Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"/><input value={query} onChange={e=>setQuery(e.target.value)} placeholder="Search reports…" className="h-10 w-full rounded-xl border border-slate-200 pl-9 pr-3 text-xs outline-none focus:border-violet-400 sm:w-48"/></div><select value={status} onChange={e=>setStatus(e.target.value)} className="h-10 rounded-xl border border-slate-200 bg-white px-2 text-xs outline-none focus:border-violet-400"><option value="All">All statuses</option>{["Submitted","Under review","Assigned","In progress","Resolved","Rejected"].map(s=><option key={s}>{s}</option>)}</select><select value={priority} onChange={e=>setPriority(e.target.value)} className="h-10 rounded-xl border border-slate-200 bg-white px-2 text-xs outline-none focus:border-violet-400"><option value="All">All priorities</option>{["Critical","High","Medium","Low"].map(s=><option key={s}>{s}</option>)}</select></div></div>{apiError && <div role="alert" className="m-5 rounded-xl bg-rose-50 p-3 text-sm text-rose-700">Could not load backend complaints: {apiError}. Start the backend and retry the page.</div>}<div className="overflow-x-auto"><table className="w-full min-w-[800px] text-left"><thead className="bg-violet-50/60 text-[10px] uppercase tracking-wider text-slate-500"><tr><th className="px-5 py-3">Issue</th><th className="px-4 py-3">Priority</th><th className="px-4 py-3">Department</th><th className="px-4 py-3">Status</th><th className="px-5 py-3 text-right">Details</th></tr></thead><tbody className="divide-y divide-slate-100">{filtered.map(c=><tr key={c.id} className="transition hover:bg-violet-50/40"><td className="px-5 py-4"><div className="font-bold text-slate-800">{c.title}</div><div className="mt-1 text-[11px] text-slate-400">{c.id} · {c.location} · {c.category}</div></td><td className="px-4 py-4"><Badge value={c.priority}/></td><td className="px-4 py-4 text-xs">{c.department}</td><td className="px-4 py-4"><Badge value={c.status}/></td><td className="px-5 py-4 text-right"><button onClick={()=>setSelected(c)} className="rounded-lg bg-violet-100 px-3 py-2 text-xs font-bold text-violet-700 hover:bg-violet-200">Open</button></td></tr>)}{filtered.length===0&&<tr><td colSpan={5} className="p-10 text-center text-sm text-slate-400">No matching reports. Try another filter.</td></tr>}</tbody></table></div><div className="border-t border-slate-100 px-5 py-3 text-[11px] text-slate-400">{loadingComplaints ? "Loading backend records…" : `Showing ${filtered.length} backend records`}</div></section>}

          {page === "Complaints" && <section className="rounded-2xl border border-violet-100 bg-white p-5"><h2 className="font-black">Issue categories</h2><div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-5">{categories.map(c=><button key={c.name} onClick={()=>{setQuery(c.name);setPriority("All");setStatus("All");}} className="rounded-2xl border border-slate-100 p-4 text-left transition hover:-translate-y-1 hover:border-violet-200 hover:shadow-lg"><span className={`flex h-10 w-10 items-center justify-center rounded-xl ${c.color}`}><c.icon size={19}/></span><div className="mt-3 text-xs font-bold">{c.name}</div><div className="mt-1 text-[10px] text-slate-400">Filter complaints →</div></button>)}</div></section>}

          {page === "Analytics" && <section className="rounded-2xl border border-violet-100 bg-white p-6"><h2 className="font-black">Analytics summary</h2><p className="mt-2 text-sm text-slate-500">Chart values are sample data. Connect your backend analytics endpoint to display real city trends.</p><div className="mt-5 grid gap-3 sm:grid-cols-3">{[{name:"Incoming reports",value:"443",c:"text-violet-600 bg-violet-50"},{name:"Resolved reports",value:"320",c:"text-emerald-600 bg-emerald-50"},{name:"Priority issues",value:String(complaints.filter(c=>c.priority==="Critical"||c.priority==="High").length),c:"text-rose-600 bg-rose-50"}].map(a=><div key={a.name} className={`rounded-2xl p-5 ${a.c}`}><div className="text-xs font-bold">{a.name}</div><div className="mt-2 text-3xl font-black">{a.value}</div></div>)}</div></section>}

          <footer className="flex flex-col justify-between gap-2 py-6 text-[10px] text-slate-400 sm:flex-row"><span>© 2026 FixMyCity AI · Civic intelligence</span><span>{apiError ? `Backend connection issue: ${apiError}` : "Complaint records are loaded from the backend. Trend chart remains illustrative."}</span></footer>
        </div>
      </section>

      {showForm && <div className="fixed inset-0 z-[100] flex items-center justify-center overflow-y-auto bg-slate-950/60 p-4 backdrop-blur-sm"><form onSubmit={submitComplaint} className="my-6 w-full max-w-xl rounded-3xl bg-white p-6 shadow-2xl sm:p-8"><div className="flex items-start justify-between"><div><div className="inline-flex items-center gap-2 rounded-full bg-orange-100 px-3 py-1 text-[10px] font-black uppercase text-orange-700"><Plus size={13}/> Citizen report</div><h2 className="mt-3 text-2xl font-black">Report an issue</h2><p className="mt-1 text-sm text-slate-500">Submit a civic report to the backend. Coordinates are required for mapping.</p></div><button type="button" onClick={()=>setShowForm(false)} className="rounded-xl bg-slate-100 p-2 hover:bg-slate-200" aria-label="Close form"><X size={18}/></button></div><label className="mt-6 block text-xs font-bold">Issue title<input required minLength={5} value={form.title} onChange={e=>setForm({...form,title:e.target.value})} placeholder="e.g. Large pothole near the school" className="mt-2 w-full rounded-xl border border-slate-200 px-4 py-3 text-sm outline-none focus:border-violet-400 focus:ring-4 focus:ring-violet-100"/></label><label className="mt-4 block text-xs font-bold">Issue category<select value={form.category} onChange={e=>setForm({...form,category:e.target.value})} className="mt-2 w-full rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm outline-none focus:border-violet-400">{categories.map(c=><option key={c.name}>{c.name}</option>)}</select></label><label className="mt-4 block text-xs font-bold">Location<input required value={form.location} onChange={e=>setForm({...form,location:e.target.value})} placeholder="Street, landmark, or ward" className="mt-2 w-full rounded-xl border border-slate-200 px-4 py-3 text-sm outline-none focus:border-violet-400 focus:ring-4 focus:ring-violet-100"/></label><div className="mt-4 grid gap-3 sm:grid-cols-2">
          <label className="block text-xs font-bold">Latitude<input required type="number" step="any" min="-90" max="90" value={latitude} onChange={e=>setLatitude(e.target.value)} placeholder="e.g. 25.4358" className="mt-2 w-full rounded-xl border border-slate-200 px-4 py-3 text-sm outline-none focus:border-violet-400"/></label>
          <label className="block text-xs font-bold">Longitude<input required type="number" step="any" min="-180" max="180" value={longitude} onChange={e=>setLongitude(e.target.value)} placeholder="e.g. 81.8463" className="mt-2 w-full rounded-xl border border-slate-200 px-4 py-3 text-sm outline-none focus:border-violet-400"/></label>
        </div>
        <button type="button" onClick={useCurrentLocation} className="mt-3 rounded-xl bg-violet-100 px-4 py-2.5 text-xs font-bold text-violet-700">Use my current location</button>
        {locationMessage && <p className="mt-2 text-xs text-slate-500">{locationMessage}</p>}
        <label className="mt-4 block text-xs font-bold">Description<textarea required minLength={5} rows={3} value={form.description} onChange={e=>setForm({...form,description:e.target.value})} placeholder="Describe the issue and its impact…" className="mt-2 w-full resize-y rounded-xl border border-slate-200 px-4 py-3 text-sm outline-none focus:border-violet-400 focus:ring-4 focus:ring-violet-100"/></label><div className="mt-6 flex flex-col-reverse gap-3 sm:flex-row sm:justify-end"><button type="button" onClick={()=>setShowForm(false)} className="rounded-xl border border-slate-200 px-5 py-3 text-sm font-bold hover:bg-slate-50">Cancel</button><button type="submit" disabled={submitting} className="inline-flex items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-violet-600 to-fuchsia-500 px-5 py-3 text-sm font-bold text-white shadow-lg shadow-violet-200 disabled:opacity-50"><Send size={15}/> {submitting ? "Submitting…" : "Submit complaint"}</button></div></form></div>}

      {selected && <div className="fixed inset-0 z-[110] flex items-center justify-center bg-slate-950/50 p-4" onClick={()=>setSelected(null)}><div role="dialog" aria-modal="true" aria-label="Complaint details" className="w-full max-w-lg rounded-3xl bg-white p-6 shadow-2xl" onClick={e=>e.stopPropagation()}><div className="flex items-start justify-between"><div><div className="text-xs font-black text-violet-600">{selected.id}</div><h2 className="mt-2 text-xl font-black">{selected.title}</h2></div><button onClick={()=>setSelected(null)} className="rounded-xl bg-slate-100 p-2" aria-label="Close details"><X size={18}/></button></div><div className="mt-5 flex flex-wrap gap-2"><Badge value={selected.priority}/><Badge value={selected.status}/></div><div className="mt-5 space-y-3 rounded-2xl bg-violet-50 p-4 text-sm"><div><span className="text-slate-500">Category: </span><strong>{selected.category}</strong></div><div><span className="text-slate-500">Location: </span><strong>{selected.location}</strong></div><div><span className="text-slate-500">Department: </span><strong>{selected.department}</strong></div></div><p className="mt-4 text-xs leading-5 text-slate-500">This record was loaded from the complaint API. Status changes and ticket history depend on the backend endpoints.</p><button onClick={()=>{setSelected(null);setPage("Live map");}} className="mt-5 w-full rounded-xl bg-gradient-to-r from-violet-600 to-fuchsia-500 py-3 text-sm font-bold text-white">View issue map</button></div></div>}

      {notice && <div role="status" className="fixed bottom-5 right-5 z-[120] flex max-w-sm items-start gap-3 rounded-2xl bg-slate-900 px-5 py-4 text-sm font-medium text-white shadow-2xl"><CheckCircle2 size={18} className="shrink-0 text-emerald-400"/><span>{notice}</span><button onClick={()=>setNotice("")} aria-label="Dismiss notification"><X size={16}/></button></div>}
    </main>
  );
}
