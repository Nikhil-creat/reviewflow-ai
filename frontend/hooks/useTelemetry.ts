"use client";
import { useCallback, useEffect, useState } from "react";
import { WS_URL } from "@/lib/config";
import type { AgentEvent } from "@/lib/types";

export type LinkState = "connecting" | "live" | "offline";

/** Live agent telemetry over WebSocket, with auto-reconnect. Pass businessId=null in demo mode. */
export function useTelemetry(businessId: string | null, onEvent?: (e: AgentEvent) => void) {
  const [events, setEvents] = useState<AgentEvent[]>([]);
  const [link, setLink] = useState<LinkState>("connecting");
  const push = useCallback((e: AgentEvent) => setEvents((p) => [e, ...p].slice(0, 150)), []);

  useEffect(() => {
    if (!businessId) return;
    let ws: WebSocket | null = null, retry: ReturnType<typeof setTimeout>, closed = false;
    const connect = () => {
      ws = new WebSocket(`${WS_URL}/ws/telemetry/${businessId}`);
      ws.onopen = () => setLink("live");
      ws.onmessage = (m) => {
        const d = JSON.parse(m.data);
        if (d.type === "backfill") setEvents(d.events as AgentEvent[]);
        else if (d.type === "event") { push(d.event); onEvent?.(d.event); }
      };
      ws.onclose = () => { setLink("offline"); if (!closed) retry = setTimeout(connect, 3500); };
      ws.onerror = () => ws?.close();
    };
    connect();
    return () => { closed = true; clearTimeout(retry); ws?.close(); };
  }, [businessId, push, onEvent]);

  return { events, link, push, setEvents };
}
