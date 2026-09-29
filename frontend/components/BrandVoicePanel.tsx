"use client";
import { useState } from "react";
import { Brain, Loader2 } from "lucide-react";

export default function BrandVoicePanel({ chunks, onIngest }: { chunks: number; onIngest: (kind: string, text: string) => Promise<void> }) {
  const [kind, setKind] = useState("past_reply");
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const submit = async () => {
    if (text.trim().length < 10) return;
    setBusy(true);
    try { await onIngest(kind, text.trim()); setText(""); } finally { setBusy(false); }
  };
  return (
    <div className="glass p-4">
      <div className="flex items-center justify-between">
        <p className="flex items-center gap-2 text-xs font-semibold uppercase tracking-widest text-slate-300"><Brain size={14} /> Brand-voice memory</p>
        <span className="rounded-md bg-neon-pink/15 px-2 py-0.5 text-[10px] font-bold text-neon-pink">{chunks} vectors</span>
      </div>
      <p className="mt-2 text-xs text-slate-400">Paste real replies, FAQs or policies. They are embedded (384-d) into pgvector and retrieved to mirror your tone.</p>
      <select value={kind} onChange={(e) => setKind(e.target.value)} className="mt-3 w-full rounded-lg border border-white/10 bg-void px-3 py-2 text-xs">
        <option value="past_reply">Past reply</option><option value="faq">FAQ / fact</option>
        <option value="policy">Policy</option><option value="tone_sample">Tone sample</option>
      </select>
      <textarea value={text} onChange={(e) => setText(e.target.value)} rows={3} placeholder="Thanks so much for visiting us! …" className="mt-2 w-full resize-none rounded-lg border border-white/10 bg-void px-3 py-2 text-xs outline-none focus:border-neon-violet" />
      <button className="btn-primary mt-2" disabled={busy} onClick={submit}>{busy ? <Loader2 size={14} className="animate-spin" /> : null} Embed into memory</button>
    </div>
  );
}
