"use client";

import { useEffect, useState, useRef } from "react";
import { apiFetch } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";

interface ActivityEvent {
  id: number;
  type: string;
  lead_id: string | null;
  payload: Record<string, unknown> | null;
  created_at: string;
}

interface Metrics {
  avg_reply_latency_s: number;
}

const INTENT_COLORS: Record<string, string> = {
  book: "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300",
  question: "bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300",
  objection: "bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-300",
  spam: "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300",
  oob: "bg-gray-100 text-gray-800 dark:bg-gray-900/30 dark:text-gray-300",
};

function formatMs(ms: number): string {
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

function isEmailEvent(type: string) {
  return type === "email_inbound" || type === "email_outbound";
}

function isChatEvent(type: string) {
  return type === "chat_message" || type === "meeting_booked";
}

export default function ActivityPage() {
  const [latencyMs, setLatencyMs] = useState<number | null>(null);
  const [inboxEvents, setInboxEvents] = useState<ActivityEvent[]>([]);
  const [chatEvents, setChatEvents] = useState<ActivityEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const eventSourceRef = useRef<EventSource | null>(null);

  useEffect(() => {
    let cancelled = false;

    const loadInitial = async () => {
      try {
        const [metricsData, activityData] = await Promise.all([
          apiFetch<Metrics>("/api/metrics"),
          apiFetch<ActivityEvent[]>("/api/activity/?limit=100"),
        ]);
        if (!cancelled) {
          setLatencyMs(Math.round(metricsData.avg_reply_latency_s * 1000));
          const all = activityData.reverse(); // newest first
          setInboxEvents(all.filter((e) => isEmailEvent(e.type)));
          setChatEvents(all.filter((e) => isChatEvent(e.type)));
        }
      } catch {
        // best-effort
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    loadInitial();

    // Poll metrics for latency banner
    const metricsInterval = setInterval(async () => {
      try {
        const data = await apiFetch<Metrics>("/api/metrics");
        if (!cancelled) setLatencyMs(Math.round(data.avg_reply_latency_s * 1000));
      } catch {
        // ignore
      }
    }, 5000);

    // SSE for live events
    const es = new EventSource(
      `${process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000"}/api/activity/stream`
    );
    eventSourceRef.current = es;

    es.onmessage = (e) => {
      try {
        const event: ActivityEvent = JSON.parse(e.data);
        if (isEmailEvent(event.type)) {
          setInboxEvents((prev) => [event, ...prev].slice(0, 100));
        } else if (isChatEvent(event.type)) {
          setChatEvents((prev) => [event, ...prev].slice(0, 100));
        }
      } catch {
        // skip malformed events
      }
    };

    es.onerror = () => {
      // EventSource auto-reconnects; nothing to do
    };

    return () => {
      cancelled = true;
      clearInterval(metricsInterval);
      es.close();
    };
  }, []);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold tracking-tight">Live Activity</h1>
      </div>

      <Card className="border-blue-200 dark:border-blue-800 bg-blue-50/50 dark:bg-blue-950/20">
        <CardContent className="py-4 text-center">
          <span className="text-sm text-muted-foreground">
            Avg. Reply Latency:{" "}
          </span>
          <span className="text-2xl font-bold text-blue-600 dark:text-blue-400">
            {latencyMs !== null ? formatMs(latencyMs) : "—"}
          </span>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>Inbox Log</CardTitle>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="space-y-2">
                {[1, 2, 3].map((i) => (
                  <Skeleton key={i} className="h-16 w-full" />
                ))}
              </div>
            ) : inboxEvents.length === 0 ? (
              <p className="text-muted-foreground text-sm">
                Waiting for activity...
              </p>
            ) : (
              <div className="space-y-0 max-h-[500px] overflow-y-auto">
                {inboxEvents.map((event, i) => {
                  const p = event.payload ?? {};
                  const isInbound = event.type === "email_inbound";
                  return (
                    <div
                      key={`${event.id}-${i}`}
                      className={`flex flex-col gap-1 py-3 border-b last:border-0 ${
                        i < 3 ? "animate-[slideIn_0.3s_ease-out]" : ""
                      }`}
                    >
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="text-xs text-muted-foreground">
                          {new Date(event.created_at).toLocaleTimeString()}
                        </span>
                        <Badge
                          variant="outline"
                          className={isInbound
                            ? "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300"
                            : "bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300"
                          }
                        >
                          {isInbound ? "Inbound" : "Outbound"}
                        </Badge>
                        {typeof p.from === "string" && (
                          <span className="text-xs font-medium">{p.from}</span>
                        )}
                        {typeof p.to === "string" && (
                          <span className="text-xs font-medium">→ {p.to}</span>
                        )}
                      </div>
                      <div className="flex items-center gap-2">
                        {typeof p.subject === "string" && (
                          <span className="text-xs font-medium truncate max-w-[200px]">
                            {p.subject}
                          </span>
                        )}
                        {typeof p.intent === "string" && (
                          <Badge
                            variant="outline"
                            className={INTENT_COLORS[String(p.intent).toLowerCase()] ?? ""}
                          >
                            {String(p.intent)}
                          </Badge>
                        )}
                        {typeof p.reply_latency_ms === "number" && (
                          <Badge variant="outline">
                            {formatMs(p.reply_latency_ms)}
                          </Badge>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Chat Log</CardTitle>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="space-y-2">
                {[1, 2, 3].map((i) => (
                  <Skeleton key={i} className="h-16 w-full" />
                ))}
              </div>
            ) : chatEvents.length === 0 ? (
              <p className="text-muted-foreground text-sm">
                Waiting for activity...
              </p>
            ) : (
              <div className="space-y-0 max-h-[500px] overflow-y-auto">
                {chatEvents.map((event, i) => {
                  const p = event.payload ?? {};
                  return (
                    <div
                      key={`${event.id}-${i}`}
                      className={`flex flex-col gap-1 py-3 border-b last:border-0 ${
                        i < 3 ? "animate-[slideIn_0.3s_ease-out]" : ""
                      }`}
                    >
                      <div className="flex items-center gap-2">
                        <span className="text-xs text-muted-foreground">
                          {new Date(event.created_at).toLocaleTimeString()}
                        </span>
                        <Badge
                          variant="outline"
                          className={
                            event.type === "meeting_booked"
                              ? "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300"
                              : "bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-300"
                          }
                        >
                          {event.type === "meeting_booked" ? "Booked" : event.type.replace(/_/g, " ")}
                        </Badge>
                      </div>
                      {typeof p.text === "string" && (
                        <p className="text-sm truncate max-w-md">{p.text}</p>
                      )}
                      {typeof p.title === "string" && (
                        <p className="text-sm font-medium text-green-700 dark:text-green-300">
                          {p.title}
                        </p>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
