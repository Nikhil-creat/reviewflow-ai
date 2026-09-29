import { API_URL } from "./config";
import type { Business, Review } from "./types";

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const r = await fetch(`${API_URL}${path}`, { ...init, headers: { "Content-Type": "application/json", ...(init?.headers || {}) } });
  if (!r.ok) throw new Error(`${r.status} ${await r.text()}`);
  return r.json();
}

export async function backendAlive(): Promise<boolean> {
  try {
    const ctl = new AbortController();
    const t = setTimeout(() => ctl.abort(), 2500);
    const r = await fetch(`${API_URL}/health`, { signal: ctl.signal });
    clearTimeout(t);
    return r.ok;
  } catch { return false; }
}

export const getBusinesses = () => req<Business[]>("/api/businesses");
export const getReviews = (id: string) => req<Review[]>(`/api/businesses/${id}/reviews`);
export const runAutopilot = (id: string) => req(`/api/businesses/${id}/autopilot/run`, { method: "POST" });
export const approveReview = (id: string, body?: string) => req(`/api/reviews/${id}/approve`, { method: "POST", body: JSON.stringify({ body }) });
export const dismissReview = (id: string) => req(`/api/reviews/${id}/dismiss`, { method: "POST" });
export const ingestBrand = (id: string, kind: string, content: string) =>
  req(`/api/businesses/${id}/brand-voice`, { method: "POST", body: JSON.stringify({ items: [{ kind, content }] }) });
export const addReview = (id: string, author_name: string, rating: number, body: string) =>
  req(`/api/businesses/${id}/reviews`, { method: "POST", body: JSON.stringify({ author_name, rating, body }) });
export const getStats = (id: string) => req<import("./types").Stats>(`/api/businesses/${id}/stats`);
