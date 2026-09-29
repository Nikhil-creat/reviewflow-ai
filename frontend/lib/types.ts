export type Sentiment = "positive" | "neutral" | "negative" | "volatile";
export type Status = "pending" | "analyzing" | "drafted" | "auto_replied" | "needs_human" | "approved" | "dismissed";
export type AgentName = "scraper" | "sentiment" | "rag_voice" | "dispatcher" | "vision" | "system";

export interface Draft { id: string; body: string; confidence: number; voice_match: number; auto_posted: boolean }
export interface Review {
  id: string; author_name: string | null; platform: string; rating: number; body: string; reviewed_at: string;
  sentiment: Sentiment | null; sentiment_score: number | null; intent_tags: string[]; risk_flags: string[];
  key_phrases: string[]; status: Status; draft: Draft | null; asset_url: string | null;
}
export interface AgentEvent {
  id: number | string; agent: AgentName; level: "info" | "success" | "warning" | "error";
  message: string; duration_ms?: number | null; created_at: string;
}
export interface Business { id: string; name: string; industry?: string | null; location?: string | null }
export interface Stats { total: number; auto_replied: number; needs_human: number; avg_rating: number; brand_chunks: number; cards: number }
