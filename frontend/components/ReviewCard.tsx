"use client";
import { motion } from "framer-motion";
import { AlertTriangle, Bot, Check, Image as ImageIcon, Star, X } from "lucide-react";
import { API_URL } from "@/lib/config";
import type { Review } from "@/lib/types";
import QuoteCard from "./QuoteCard";

const BADGE: Record<string, string> = {
  positive: "bg-emerald-500/15 text-emerald-300", neutral: "bg-slate-500/20 text-slate-300",
  negative: "bg-orange-500/15 text-orange-300", volatile: "bg-red-500/15 text-red-300",
};
const STATUS: Record<string, string> = {
  pending: "Queued", analyzing: "Analyzing…", drafted: "Drafted", auto_replied: "Auto-replied",
  needs_human: "Needs you", approved: "Approved", dismissed: "Dismissed",
};

export default function ReviewCard({ r, business, onApprove, onDismiss }: {
  r: Review; business: string; onApprove: (r: Review) => void; onDismiss: (r: Review) => void;
}) {
  const needs = r.status === "needs_human" || (r.status === "drafted" && !r.draft?.auto_posted);
  const cardQuote = r.key_phrases[0] || r.body.slice(0, 90);
  return (
    <motion.article layout initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} className={`glass p-4 ${r.status === "needs_human" ? "ring-1 ring-amber-400/50" : ""}`}>
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-sm font-semibold">{r.author_name || "Anonymous"} <span className="ml-1 text-xs font-normal text-slate-500">{r.platform}</span></p>
          <div className="mt-0.5 flex">{[1, 2, 3, 4, 5].map((i) => <Star key={i} size={13} className={i <= r.rating ? "fill-amber-400 text-amber-400" : "text-slate-700"} />)}</div>
        </div>
        <span className={`rounded-full px-2.5 py-1 text-[10px] font-bold uppercase tracking-wider ${r.status === "needs_human" ? "bg-amber-400/15 text-amber-300" : "bg-white/8 text-slate-300"}`}>{STATUS[r.status]}</span>
      </div>

      <p className="mt-3 text-sm leading-relaxed text-slate-200">{r.body}</p>

      <div className="mt-3 flex flex-wrap items-center gap-1.5">
        {r.sentiment && <span className={`rounded-md px-2 py-0.5 text-[10px] font-bold uppercase ${BADGE[r.sentiment]}`}>{r.sentiment}{r.sentiment_score !== null ? ` ${r.sentiment_score > 0 ? "+" : ""}${r.sentiment_score.toFixed(2)}` : ""}</span>}
        {r.risk_flags.map((f) => <span key={f} className="flex items-center gap-1 rounded-md bg-red-500/15 px-2 py-0.5 text-[10px] font-bold text-red-300"><AlertTriangle size={10} />{f}</span>)}
        {r.intent_tags.map((t) => <span key={t} className="rounded-md bg-white/6 px-2 py-0.5 text-[10px] text-slate-400">#{t}</span>)}
      </div>

      {r.draft && (
        <div className="mt-3 rounded-xl border border-neon-violet/25 bg-neon-violet/5 p-3">
          <p className="flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-widest text-neon-violet"><Bot size={12} /> AI reply in your voice</p>
          <p className="mt-1.5 text-sm text-slate-200">{r.draft.body}</p>
          <div className="mt-2 grid grid-cols-2 gap-3 text-[10px] text-slate-400">
            <Meter label="Confidence" v={r.draft.confidence} />
            <Meter label="Voice match" v={r.draft.voice_match} />
          </div>
        </div>
      )}

      {r.asset_url && (
        <div className="mt-3">
          <p className="mb-1.5 flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-widest text-neon-amber"><ImageIcon size={12} /> Social quote card</p>
          {r.asset_url === "demo"
            ? <QuoteCard quote={cardQuote} author={r.author_name || "Customer"} business={business} />
            : <img src={`${API_URL}${r.asset_url}`} alt="Generated quote card" className="w-full max-w-xs rounded-xl" />}
        </div>
      )}

      {needs && r.draft && (
        <div className="mt-3 flex gap-2">
          <button className="btn-primary" onClick={() => onApprove(r)}><Check size={14} /> Approve &amp; post</button>
          <button className="btn-ghost" onClick={() => onDismiss(r)}><X size={14} /> Dismiss</button>
        </div>
      )}
    </motion.article>
  );
}

function Meter({ label, v }: { label: string; v: number }) {
  return (
    <div>
      <div className="flex justify-between"><span>{label}</span><span>{Math.round(v * 100)}%</span></div>
      <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-white/10">
        <div className="h-full rounded-full bg-gradient-to-r from-neon-cyan to-neon-violet" style={{ width: `${Math.round(v * 100)}%` }} />
      </div>
    </div>
  );
}
