"use client";
import { motion } from "framer-motion";
import { Database, Eye, Radar, Send, ShieldCheck } from "lucide-react";
import type { AgentName } from "@/lib/types";

const NODES: { id: AgentName; label: string; sub: string; icon: any; color: string }[] = [
  { id: "scraper", label: "Sync", sub: "fetch reviews", icon: Radar, color: "#22d3ee" },
  { id: "sentiment", label: "Sentiment", sub: "classify + risk", icon: ShieldCheck, color: "#a78bfa" },
  { id: "rag_voice", label: "RAG Voice", sub: "pgvector + Llama", icon: Database, color: "#f472b6" },
  { id: "dispatcher", label: "Dispatcher", sub: "auto-reply / flag", icon: Send, color: "#a3e635" },
  { id: "vision", label: "Vision CNN", sub: "quote cards", icon: Eye, color: "#fbbf24" },
];

export default function PipelineVisualizer({ active }: { active: AgentName | null }) {
  return (
    <div className="glass p-4">
      <p className="mb-3 text-xs font-semibold uppercase tracking-widest text-slate-400">LangGraph autopilot</p>
      <div className="flex items-stretch gap-2 overflow-x-auto">
        {NODES.map((n, i) => {
          const on = active === n.id;
          const Icon = n.icon;
          return (
            <div key={n.id} className="flex flex-1 items-center gap-2">
              <motion.div
                animate={{ scale: on ? 1.05 : 1, boxShadow: on ? `0 0 28px ${n.color}66` : "0 0 0 transparent" }}
                className="relative min-w-[92px] flex-1 rounded-xl border p-3 text-center"
                style={{ borderColor: on ? n.color : "rgba(255,255,255,.09)", background: on ? `${n.color}14` : "rgba(255,255,255,.02)" }}
              >
                {on && <motion.span className="absolute inset-0 rounded-xl border" style={{ borderColor: n.color }} animate={{ opacity: [0.9, 0, 0.9], scale: [1, 1.12, 1] }} transition={{ duration: 1.4, repeat: Infinity }} />}
                <Icon size={20} className="mx-auto" style={{ color: n.color }} />
                <p className="mt-1 text-xs font-bold">{n.label}</p>
                <p className="text-[10px] text-slate-400">{n.sub}</p>
              </motion.div>
              {i < NODES.length - 1 && <span className="text-slate-600">›</span>}
            </div>
          );
        })}
      </div>
    </div>
  );
}
