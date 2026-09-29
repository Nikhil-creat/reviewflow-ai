"use client";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { AnimatePresence } from "framer-motion";
import { ArrowLeft, Loader2, Play, Sparkles } from "lucide-react";
import BrandVoicePanel from "@/components/BrandVoicePanel";
import Credit from "@/components/Credit";
import PipelineVisualizer from "@/components/PipelineVisualizer";
import ReviewCard from "@/components/ReviewCard";
import TelemetryFeed from "@/components/TelemetryFeed";
import { useTelemetry } from "@/hooks/useTelemetry";
import * as api from "@/lib/api";
import { DEMO_REVIEWS, runDemoAutopilot } from "@/lib/demo";
import type { AgentEvent, AgentName, Business, Review } from "@/lib/types";

const FILTERS = [
  { id: "all", label: "All" }, { id: "needs_human", label: "Needs you" },
  { id: "auto_replied", label: "Auto-replied" }, { id: "pending", label: "Queued" },
];

export default function Dashboard() {
  const [demo, setDemo] = useState<boolean | null>(null);
  const [business, setBusiness] = useState<Business>({ id: "demo", name: "Blue Lotus Café" });
  const [reviews, setReviews] = useState<Review[]>([]);
  const [brandChunks, setBrandChunks] = useState(7);
  const [active, setActive] = useState<AgentName | null>(null);
  const [running, setRunning] = useState(false);
  const [filter, setFilter] = useState("all");
  const [error, setError] = useState<string | null>(null);

  const bizId = useRef<string | null>(null);
  const refreshTimer = useRef<ReturnType<typeof setTimeout>>();

  const refresh = useCallback(async () => {
    if (!bizId.current) return;
    try {
      const [rv, st] = await Promise.all([api.getReviews(bizId.current), api.getStats(bizId.current)]);
      setReviews(rv); setBrandChunks(Number(st.brand_chunks));
    } catch (e: any) { setError(e.message); }
  }, []);

  const onLiveEvent = useCallback((e: AgentEvent) => {
    setActive(e.agent);
    if (e.agent === "system" && /complete|failed/i.test(e.message)) { setRunning(false); setActive(null); }
    clearTimeout(refreshTimer.current);
    refreshTimer.current = setTimeout(refresh, 400);
  }, [refresh]);

  const { events, link, push } = useTelemetry(demo === false ? business.id : null, onLiveEvent);

  // boot: live backend if reachable, otherwise the offline simulation
  useEffect(() => {
    (async () => {
      if (await api.backendAlive()) {
        try {
          const list = await api.getBusinesses();
          if (list.length) { setBusiness(list[0]); bizId.current = list[0].id; setDemo(false); await refresh(); return; }
        } catch { /* fall through to demo */ }
      }
      setReviews(DEMO_REVIEWS); setDemo(true);
    })();
  }, [refresh]);

  const run = async () => {
    setRunning(true); setError(null);
    if (demo) {
      await runDemoAutopilot(
        reviews, push,
        (id, patch) => setReviews((p) => p.map((r) => (r.id === id ? { ...r, ...patch } : r))),
        setActive,
      );
      setRunning(false);
    } else {
      try { await api.runAutopilot(business.id); setTimeout(() => setRunning(false), 90000); }
      catch (e: any) { setError(e.message); setRunning(false); }
    }
  };

  const approve = async (r: Review) => {
    if (demo) return setReviews((p) => p.map((x) => (x.id === r.id ? { ...x, status: "approved" } : x)));
    try { await api.approveReview(r.id); await refresh(); } catch (e: any) { setError(e.message); }
  };
  const dismiss = async (r: Review) => {
    if (demo) return setReviews((p) => p.map((x) => (x.id === r.id ? { ...x, status: "dismissed" } : x)));
    try { await api.dismissReview(r.id); await refresh(); } catch (e: any) { setError(e.message); }
  };
  const ingest = async (kind: string, text: string) => {
    if (demo) {
      setBrandChunks((c) => c + 1);
      push({ id: `d-${Date.now()}`, agent: "rag_voice", level: "success", message: "Embedded 1 brand-voice chunk into pgvector", duration_ms: 23, created_at: new Date().toISOString() });
      return;
    }
    try { await api.ingestBrand(business.id, kind, text); await refresh(); } catch (e: any) { setError(e.message); }
  };

  const stats = useMemo(() => {
    const n = reviews.length || 1;
    return {
      total: reviews.length,
      auto: reviews.filter((r) => r.status === "auto_replied").length,
      human: reviews.filter((r) => r.status === "needs_human").length,
      avg: (reviews.reduce((s, r) => s + r.rating, 0) / n).toFixed(1),
    };
  }, [reviews]);

  const shown = reviews.filter((r) => filter === "all" ? r.status !== "dismissed" : r.status === filter);

  return (
    <main className="mx-auto max-w-7xl px-4 py-6 md:px-6">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <Link href="/" className="btn-ghost !px-2.5"><ArrowLeft size={14} /></Link>
          <div>
            <h1 className="flex items-center gap-2 text-xl font-extrabold"><Sparkles size={18} className="text-neon-cyan" /> ReviewFlow <span className="neon-text">AI</span></h1>
            <p className="text-xs text-slate-400">{business.name}{business.location ? ` · ${business.location}` : ""}</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          {demo !== null && <span className={`rounded-full px-3 py-1 text-[10px] font-bold tracking-widest ${demo ? "bg-neon-amber/15 text-neon-amber" : "bg-emerald-400/15 text-emerald-300"}`}>{demo ? "DEMO MODE · NO BACKEND" : "LIVE BACKEND"}</span>}
          <button className="btn-primary" onClick={run} disabled={running || demo === null}>
            {running ? <Loader2 size={14} className="animate-spin" /> : <Play size={14} />} Run autopilot
          </button>
        </div>
      </header>

      {error && <p className="mt-4 rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-xs text-red-300">{error}</p>}

      <section className="mt-6 grid grid-cols-2 gap-3 md:grid-cols-4">
        {[["Reviews", stats.total, "text-neon-cyan"], ["Auto-replied", stats.auto, "text-neon-lime"], ["Needs you", stats.human, "text-neon-amber"], ["Avg rating", stats.avg, "text-neon-pink"]].map(([l, v, c]) => (
          <div key={l as string} className="glass p-4"><p className="text-[10px] uppercase tracking-widest text-slate-400">{l}</p><p className={`mt-1 text-3xl font-extrabold ${c}`}>{v}</p></div>
        ))}
      </section>

      <div className="mt-4"><PipelineVisualizer active={active} /></div>

      <div className="mt-4 grid gap-4 lg:grid-cols-12">
        <section className="space-y-3 lg:col-span-7">
          <div className="flex gap-2 overflow-x-auto">
            {FILTERS.map((f) => (
              <button key={f.id} onClick={() => setFilter(f.id)} className={`btn ${filter === f.id ? "bg-white/15" : "bg-white/5 hover:bg-white/10"} !py-1.5 text-xs`}>{f.label}</button>
            ))}
          </div>
          <AnimatePresence initial={false}>
            {shown.map((r) => <ReviewCard key={r.id} r={r} business={business.name} onApprove={approve} onDismiss={dismiss} />)}
          </AnimatePresence>
          {shown.length === 0 && <p className="glass p-6 text-center text-sm text-slate-400">Nothing here yet. Run the autopilot to pull in new reviews.</p>}
        </section>

        <aside className="space-y-4 lg:col-span-5">
          <TelemetryFeed events={events} link={link} demo={demo === true} />
          <BrandVoicePanel chunks={brandChunks} onIngest={ingest} />
        </aside>
      </div>
      <Credit className="mt-6" />
    </main>
  );
}
