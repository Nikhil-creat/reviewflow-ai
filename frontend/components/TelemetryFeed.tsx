"use client";
import { AnimatePresence, motion } from "framer-motion";
import { Activity } from "lucide-react";
import type { LinkState } from "@/hooks/useTelemetry";
import type { AgentEvent, AgentName } from "@/lib/types";

const COLORS: Record<AgentName, string> = {
  scraper: "text-neon-cyan", sentiment: "text-neon-violet", rag_voice: "text-neon-pink",
  dispatcher: "text-neon-lime", vision: "text-neon-amber", system: "text-slate-300",
};
const LEVEL: Record<string, string> = { info: "text-slate-300", success: "text-emerald-300", warning: "text-amber-300", error: "text-red-400" };

export default function TelemetryFeed({ events, link, demo }: { events: AgentEvent[]; link: LinkState; demo: boolean }) {
  const label = demo ? "SIMULATED" : link === "live" ? "LIVE" : link === "connecting" ? "CONNECTING" : "RECONNECTING";
  const dot = demo ? "bg-neon-amber" : link === "live" ? "bg-emerald-400" : "bg-red-400";
  return (
    <div className="glass relative flex h-[420px] flex-col overflow-hidden">
      <div className="flex items-center justify-between border-b border-white/10 px-4 py-3">
        <span className="flex items-center gap-2 text-xs font-semibold uppercase tracking-widest text-slate-300"><Activity size={14} /> Agent telemetry</span>
        <span className="flex items-center gap-2 text-[10px] font-bold tracking-widest text-slate-300">
          <span className={`h-2 w-2 animate-pulse rounded-full ${dot}`} />{label}
        </span>
      </div>
      <div className="pointer-events-none absolute inset-x-0 top-10 h-20 animate-scan bg-gradient-to-b from-neon-cyan/10 to-transparent" />
      <div className="flex-1 space-y-1 overflow-y-auto px-4 py-3 font-mono text-[11.5px] leading-relaxed">
        {events.length === 0 && <p className="text-slate-500">Waiting for agent activity… press “Run autopilot”.</p>}
        <AnimatePresence initial={false}>
          {events.map((e) => (
            <motion.div key={e.id} initial={{ opacity: 0, x: -12 }} animate={{ opacity: 1, x: 0 }} className="flex gap-2">
              <span className="shrink-0 text-slate-600">{new Date(e.created_at).toLocaleTimeString([], { hour12: false })}</span>
              <span className={`w-20 shrink-0 font-bold ${COLORS[e.agent] ?? "text-slate-300"}`}>{e.agent}</span>
              <span className={LEVEL[e.level]}>{e.message}{e.duration_ms ? <span className="text-slate-500"> · {e.duration_ms}ms</span> : null}</span>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </div>
  );
}
