// Offline simulation so the static GitHub Pages / Vercel build works without a backend.
import type { AgentEvent, AgentName, Review } from "./types";

const ago = (m: number) => new Date(Date.now() - m * 60000).toISOString();
const base = (o: Partial<Review> & Pick<Review, "id" | "author_name" | "rating" | "body">): Review => ({
  platform: "google", reviewed_at: ago(30), sentiment: null, sentiment_score: null, intent_tags: [], risk_flags: [],
  key_phrases: [], status: "pending", draft: null, asset_url: null, ...o,
});

export const DEMO_REVIEWS: Review[] = [
  base({ id: "d1", author_name: "Ananya R.", rating: 5, reviewed_at: ago(12), body: "Absolutely loved the filter coffee and the warm staff. Best cozy corner in the city!" }),
  base({ id: "d2", author_name: "Meera D.", rating: 1, reviewed_at: ago(25), body: "Found a hair in my food. I'm going to contact a lawyer and the health department if this isn't fixed." }),
  base({ id: "d3", author_name: "Rahul P.", rating: 3, reviewed_at: ago(41), body: "Coffee was good but we waited 25 minutes for a table even with a booking." }),
  base({ id: "d4", author_name: "Arjun T.", rating: 5, reviewed_at: ago(66), body: "Every dish felt handmade. The owner even remembered my name. Five stars!" }),
];

interface Outcome {
  sentiment: Review["sentiment"]; score: number; tags: string[]; risks: string[]; phrase: string;
  draft: string; conf: number; match: number; sim: number; status: Review["status"];
}
const OUTCOMES: Record<string, Outcome> = {
  d1: { sentiment: "positive", score: 0.94, tags: ["coffee", "staff"], risks: [], phrase: "Best cozy corner in the city!", conf: 0.93, match: 0.74, sim: 0.74, status: "auto_replied",
    draft: "Thank you so much, Ananya! 🌸 It means the world to our little café team. Your next filter coffee is on us - see you soon! - Priya & the Blue Lotus family" },
  d2: { sentiment: "volatile", score: -0.92, tags: ["food_quality", "hygiene"], risks: ["legal_threat", "safety_issue"], phrase: "", conf: 0.41, match: 0.58, sim: 0.58, status: "needs_human",
    draft: "Hi Meera, we're truly sorry - this is not the standard we hold ourselves to. Please write to hello@bluelotus.example so I can make this right personally. - Priya" },
  d3: { sentiment: "neutral", score: 0.05, tags: ["wait_time", "booking"], risks: [], phrase: "", conf: 0.71, match: 0.69, sim: 0.69, status: "needs_human",
    draft: "Hi Rahul, thank you for telling us about the wait - that's not the experience we want for anyone. Please write to us and we'll sort your next booking personally. - Priya" },
  d4: { sentiment: "positive", score: 0.96, tags: ["food", "owner"], risks: [], phrase: "Every dish felt handmade.", conf: 0.91, match: 0.71, sim: 0.71, status: "auto_replied",
    draft: "Arjun, that made our day! We do hand-make everything in-house every morning. Come hungry next time 🥐 - Priya" },
};

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));
let eid = 0;
const ev = (agent: AgentName, message: string, level: AgentEvent["level"] = "info", ms?: number): AgentEvent =>
  ({ id: `demo-${++eid}`, agent, level, message, duration_ms: ms ?? null, created_at: new Date().toISOString() });

/** Replays the same steps the real LangGraph autopilot emits. */
export async function runDemoAutopilot(
  reviews: Review[],
  onEvent: (e: AgentEvent) => void,
  onUpdate: (id: string, patch: Partial<Review>) => void,
  onAgent: (a: AgentName | null) => void,
) {
  onAgent("system"); onEvent(ev("system", "Autopilot run started (manual)")); await sleep(500);
  onAgent("scraper"); onEvent(ev("scraper", "Sync agent connecting to source 'demo'…")); await sleep(700);
  const queue = reviews.filter((r) => r.status === "pending");
  onEvent(ev("scraper", `Sync complete: ${queue.length} queued for the autopilot`, "success", 184)); await sleep(500);

  for (const rv of queue) {
    const o = OUTCOMES[rv.id]; if (!o) continue;
    onAgent("sentiment"); onUpdate(rv.id, { status: "analyzing" });
    onEvent(ev("sentiment", `Agent evaluating sentiment: ${rv.author_name} (${rv.rating}★)…`)); await sleep(650);
    onUpdate(rv.id, { sentiment: o.sentiment, sentiment_score: o.score, intent_tags: o.tags, risk_flags: o.risks, key_phrases: o.phrase ? [o.phrase] : [] });
    onEvent(ev("sentiment", `Sentiment ${o.sentiment} (${o.score >= 0 ? "+" : ""}${o.score.toFixed(2)}) · tags: ${o.tags.join(", ")}` + (o.risks.length ? ` · RISK: ${o.risks.join(", ")}` : ""),
      o.risks.length ? "warning" : "success", 41)); await sleep(500);

    onAgent("rag_voice");
    onEvent(ev("rag_voice", `Vector search complete (12ms): 5 chunks, mean similarity ${o.sim.toFixed(2)}`, "success", 12)); await sleep(550);
    onUpdate(rv.id, { status: "drafted", draft: { id: `dr-${rv.id}`, body: o.draft, confidence: o.conf, voice_match: o.match, auto_posted: false } });
    onEvent(ev("rag_voice", `Reply drafted in owner's voice · confidence ${o.conf.toFixed(2)}`, "success", 318)); await sleep(500);

    onAgent("dispatcher");
    if (o.status === "auto_replied") {
      onUpdate(rv.id, { status: "auto_replied", draft: { id: `dr-${rv.id}`, body: o.draft, confidence: o.conf, voice_match: o.match, auto_posted: true } });
      onEvent(ev("dispatcher", `Auto-replied to ${rv.author_name} (safe, confidence ${o.conf.toFixed(2)})`, "success"));
    } else {
      onUpdate(rv.id, { status: "needs_human" });
      onEvent(ev("dispatcher", o.risks.length ? `Flagged for human review: sentiment ${o.sentiment}; risk: ${o.risks.join(", ")}` : `Flagged for human review: confidence ${o.conf.toFixed(2)} < 0.85`, "warning"));
    }
    await sleep(500);

    if (rv.rating === 5 && o.sentiment === "positive") {
      onAgent("vision"); onEvent(ev("vision", "Vision pipeline rendering social quote card…")); await sleep(800);
      onUpdate(rv.id, { asset_url: "demo" });
      onEvent(ev("vision", "Quote card ready (bottom band, dark text) · 640ms", "success", 640)); await sleep(400);
    }
  }
  onAgent("system");
  onEvent(ev("system", `Run complete: ${queue.length} reviews · 2 auto-replied · 2 flagged · 2 cards`, "success"));
  await sleep(600); onAgent(null);
}
