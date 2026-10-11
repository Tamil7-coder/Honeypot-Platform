import { createContext, useContext, useEffect, useRef, useState, ReactNode, useCallback } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useAuth } from "./AuthContext";

export interface LiveEvent {
  key: string;
  type: "new_attack" | "new_alert";
  data: Record<string, unknown>;
  receivedAt: number;
}

interface LiveFeedContextValue {
  isConnected: boolean;
  events: LiveEvent[];
  unreadAlertCount: number;
  clearUnreadAlerts: () => void;
}

const LiveFeedContext = createContext<LiveFeedContextValue | undefined>(undefined);

const MAX_EVENTS = 25;
const MAX_BACKOFF_MS = 15_000;

function resolveWebSocketUrl(): string {
  const apiBase = import.meta.env.VITE_API_BASE_URL || "/api/v1";
  const token = localStorage.getItem("access_token") ?? "";

  if (apiBase.startsWith("http")) {
    const wsBase = apiBase.replace(/^http/, "ws");
    return `${wsBase}/ws/live?token=${encodeURIComponent(token)}`;
  }

  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${protocol}//${window.location.host}${apiBase}/ws/live?token=${encodeURIComponent(token)}`;
}

export function LiveFeedProvider({ children }: { children: ReactNode }) {
  const { isAuthenticated } = useAuth();
  const queryClient = useQueryClient();

  const [isConnected, setIsConnected] = useState(false);
  const [events, setEvents] = useState<LiveEvent[]>([]);
  const [unreadAlertCount, setUnreadAlertCount] = useState(0);

  const socketRef = useRef<WebSocket | null>(null);
  const reconnectAttemptRef = useRef(0);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const shouldReconnectRef = useRef(true);

  const clearUnreadAlerts = useCallback(() => setUnreadAlertCount(0), []);

  useEffect(() => {
    shouldReconnectRef.current = isAuthenticated;

    if (!isAuthenticated) {
      socketRef.current?.close();
      return;
    }

    function connect() {
      const socket = new WebSocket(resolveWebSocketUrl());
      socketRef.current = socket;

      socket.onopen = () => {
        setIsConnected(true);
        reconnectAttemptRef.current = 0;
      };

      socket.onmessage = (event) => {
        try {
          const parsed = JSON.parse(event.data) as { type: LiveEvent["type"]; data: Record<string, unknown> };

          setEvents((prev) =>
            [{ key: `${Date.now()}-${Math.random()}`, ...parsed, receivedAt: Date.now() }, ...prev].slice(
              0,
              MAX_EVENTS
            )
          );

          if (parsed.type === "new_alert") {
            setUnreadAlertCount((n) => n + 1);
          }

          // WS payloads are lightweight signals — the source of truth for
          // aggregated numbers stays the REST endpoints; this just triggers
          // an immediate refetch instead of waiting for the next poll.
          queryClient.invalidateQueries({ queryKey: ["dashboard-summary"] });
          queryClient.invalidateQueries({ queryKey: ["attack-sessions"] });
          if (parsed.type === "new_alert") {
            queryClient.invalidateQueries({ queryKey: ["notifications"] });
          }
        } catch {
          // ignore malformed frames
        }
      };

      socket.onclose = () => {
        setIsConnected(false);
        socketRef.current = null;
        if (!shouldReconnectRef.current) return;

        const attempt = reconnectAttemptRef.current + 1;
        reconnectAttemptRef.current = attempt;
        const delay = Math.min(1000 * 2 ** attempt, MAX_BACKOFF_MS);
        reconnectTimerRef.current = setTimeout(connect, delay);
      };

      socket.onerror = () => {
        socket.close();
      };
    }

    connect();

    return () => {
      shouldReconnectRef.current = false;
      if (reconnectTimerRef.current) clearTimeout(reconnectTimerRef.current);
      socketRef.current?.close();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isAuthenticated]);

  return (
    <LiveFeedContext.Provider value={{ isConnected, events, unreadAlertCount, clearUnreadAlerts }}>
      {children}
    </LiveFeedContext.Provider>
  );
}

export function useLiveFeed(): LiveFeedContextValue {
  const ctx = useContext(LiveFeedContext);
  if (!ctx) throw new Error("useLiveFeed must be used within LiveFeedProvider");
  return ctx;
}
