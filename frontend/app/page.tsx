"use client";
import Link from "next/link";
import { motion } from "framer-motion";
import { ArrowRight, Brain, Eye, Radar, ShieldCheck, Sparkles, Zap } from "lucide-react";
import Credit from "@/components/Credit";
import { CREDIT } from "@/lib/config";

const FEATURES = [
  { icon: Radar, t: "Autonomous agent loop", d: "A LangGraph state machine syncs reviews, scores sentiment, drafts replies and dispatches - or escalates volatile ones to you.", c: "text-neon-cyan" },
  { icon: Brain, t: "RAG brand-voice engine", d: "Your past replies live in pgvector. Every draft retrieves your real tone, sign-offs and facts before it writes a word.", c: "text-neon-pink" },
  { icon: Eye, t: "CNN vision cards", d: "Convolutional layout analysis picks the calmest region and text colour, then renders share-ready quote cards from 5-star reviews.", c: "text-neon-amber" },
  { icon: Zap, t: "Groq-speed inference", d: "Llama models on Groq's free tier answer in well under a second. Zero-cost embeddings run locally in the container.", c: "text-neon-lime" },
];
const PLANS = [
  { n: "Free", p: "$0", f: ["1 location", "50 AI replies / mo", "Manual approval"], h: false },
  { n: "Pro", p: "$29", f: ["5 locations", "Unlimited replies", "Auto-reply + quote cards", "Priority telemetry"], h: true },
  { n: "Agency", p: "$99", f: ["25 locations", "Team seats", "White-label cards", "API access"], h: false },
];

export default function Landing() {
  return (
    <main className="relative overflow-hidden">
      <div className="bg-grid pointer-events-none absolute inset-0 h-[720px]" />
      <nav className="relative mx-auto flex max-w-6xl items-center justify-between px-6 py-5">
        <span className="flex items-center gap-2 font-bold"><Sparkles className="text-neon-cyan" size={20} /> ReviewFlow <span className="neon-text">AI</span></span>
        <Link href="/dashboard" className="btn-ghost">Open dashboard <ArrowRight size={14} /></Link>
      </nav>

      <section className="relative mx-auto max-w-4xl px-6 pb-20 pt-16 text-center">
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.7 }}>
          <span className="glass inline-flex items-center gap-2 px-3 py-1 text-xs text-slate-300"><ShieldCheck size={13} className="text-neon-lime" /> Agentic AI · RAG · CNN · Docker</span>
          <h1 className="mt-6 text-5xl font-extrabold leading-tight md:text-7xl">Your reputation,<br /><span className="neon-text">on autopilot.</span></h1>
          <p className="mx-auto mt-6 max-w-2xl text-lg text-slate-300">ReviewFlow answers every review in your exact voice, flags the risky ones for you, and turns your best praise into social posts - while you run your business.</p>
          <div className="mt-8 flex justify-center gap-3">
            <Link href="/dashboard" className="btn-primary">Launch live demo <ArrowRight size={14} /></Link>
            <a href="#pricing" className="btn-ghost">See pricing</a>
          </div>
        </motion.div>
        <motion.div animate={{ y: [0, -14, 0] }} transition={{ duration: 7, repeat: Infinity }} className="pointer-events-none absolute -right-10 top-24 hidden h-40 w-40 rounded-full bg-neon-violet/30 blur-3xl md:block" />
      </section>

      <section className="relative mx-auto grid max-w-6xl gap-4 px-6 md:grid-cols-2">
        {FEATURES.map((f, i) => (
          <motion.div key={f.t} initial={{ opacity: 0, y: 24 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ delay: i * 0.08 }} className="glass p-6">
            <f.icon className={f.c} size={26} />
            <h3 className="mt-3 text-lg font-bold">{f.t}</h3>
            <p className="mt-1 text-sm text-slate-400">{f.d}</p>
          </motion.div>
        ))}
      </section>

      <section id="pricing" className="relative mx-auto max-w-5xl px-6 py-24">
        <h2 className="text-center text-3xl font-extrabold">Simple, <span className="neon-text">monetizable</span> pricing</h2>
        <div className="mt-10 grid gap-4 md:grid-cols-3">
          {PLANS.map((p) => (
            <div key={p.n} className={`glass p-6 ${p.h ? "ring-2 ring-neon-violet" : ""}`}>
              <p className="text-sm font-semibold text-slate-300">{p.n}</p>
              <p className="mt-2 text-4xl font-extrabold">{p.p}<span className="text-sm font-normal text-slate-500"> / mo</span></p>
              <ul className="mt-4 space-y-2 text-sm text-slate-300">{p.f.map((x) => <li key={x}>✓ {x}</li>)}</ul>
              <a
                href={`mailto:${CREDIT.email}?subject=${encodeURIComponent(`ReviewFlow AI - ${p.n} plan`)}&body=${encodeURIComponent(`Hi, I'd like to subscribe to the ${p.n} plan ($${p.p}/mo).`)}`}
                className="btn-primary mt-5 w-full justify-center"
              >
                Contact to subscribe
              </a>
            </div>
          ))}
        </div>
      </section>
      <Credit />
    </main>
  );
}
