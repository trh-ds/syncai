"use client";

import { useEffect, useState, useRef } from "react";
import { apiFetch } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";

interface ActivityEvent {
  id: string;
  type: string;
  sub_type: string;
  timestamp: string;
  data: Record<string, unknown>;
}

interface Metrics {
  avg_reply_latency_s: number;
}

const INTENT_COLORS: Record<string, string> = {
  high: "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300",
  medium: "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300",
  low: "bg-gray-100 text-gray-800 dark:bg-gray-900/30 dark:text-gray-300",
};

function formatMs(ms: number): string {
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

export default function ActivityPage() {
  const [latencyMs, setLatencyMs] = useState<number | null>(null);
  const [inboxEvents, setInboxEvents] = useState<ActivityEvent[]>([]);
  const [chatEvents, setChatEvents] = useState<ActivityEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const eventSourceRef = useRef<EventSource | null>(null);

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        const data = await apiFetch<Metrics>("/api/metrics");
        if (!cancelled) {
          setLatencyMs(Math.round(data.avg_reply_latency_s * 1000));
        }
      } catch {
        // best-effort
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    load();

    const es = new EventSource(
      `${process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000"}/api/activity/stream`
    );
    eventSourceRef.current = es;

    es.onmessage = (e) => {
      try {
        const event: ActivityEvent = JSON.parse(e.data);
        if (
          event.type === "email_sent" ||
          event.type === "email_received"
        ) {
          setInboxEvents((prev) => [event, ...prev].slice(0, 100));
        } else if (event.type === "chat_message") {
          setChatEvents((prev) => [event, ...prev].slice(0, 100));
        }
      } catch {
        // skip malformed events
      }
    };

    es.onerror = () => {
      setError("Activity stream disconnected");
    };

    return () => {
      cancelled = true;
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
            {error && inboxEvents.length === 0 && (
              <p className="text-destructive text-sm mb-3">{error}</p>
            )}
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
              <div className="space-y-0">
                {inboxEvents.map((event, i) => (
                  <div
                    key={event.id}
                    className={`flex flex-col gap-1 py-3 border-b last:border-0 ${
                      i < 3 ? "animate-slide-in" : ""
                    }`}
                  >
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-xs text-muted-foreground">
                        {new Date(event.timestamp).toLocaleTimeString()}
                      </span>
                      <span className="text-xs font-medium">
                        {event.data &&
                        typeof event.data === "object" &&
                        "from" in event.data
                          ? String(event.data.from)
                          : "—"}
                      </span>
                      {event.data &&
                        typeof event.data === "object" &&
                        "subject" in event.data && (
                          <span className="text-xs font-medium truncate max-w-[200px]">
                            {String(event.data.subject)}
                          </span>
                        )}
                    </div>
                    <div className="flex items-center gap-2">
                      {event.data &&
                        typeof event.data === "object" &&
                        "intent" in event.data && (
                          <Badge
                            variant="outline"
                            className={
                              INTENT_COLORS[
                                String(event.data.intent).toLowerCase()
                              ] ?? ""
                            }
                          >
                            {String(event.data.intent)}
                          </Badge>
                        )}
                      {event.data &&
                        typeof event.data === "object" &&
                        "reply_latency_ms" in event.data && (
                          <Badge variant="outline">
                            {formatMs(Number(event.data.reply_latency_ms))}
                          </Badge>
                        )}
                    </div>
                    {event.data &&
                      typeof event.data === "object" &&
                      "ai_reply" in event.data && (
                        <p className="text-xs text-muted-foreground truncate max-w-md">
                          {String(event.data.ai_reply)}
                        </p>
                      )}
                  </div>
                ))}
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
              <div className="space-y-0">
                {chatEvents.map((event, i) => (
                  <div
                    key={event.id}
                    className={`flex flex-col gap-1 py-3 border-b last:border-0 ${
                      i < 3 ? "animate-slide-in" : ""
                    }`}
                  >
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-muted-foreground">
                        {new Date(event.timestamp).toLocaleTimeString()}
                      </span>
                      <Badge
                        variant="outline"
                        className={
                          event.sub_type === "inbound"
                            ? "bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300"
                            : "bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-300"
                        }
                      >
                        {event.sub_type}
                      </Badge>
                      {event.data &&
                        typeof event.data === "object" &&
                        "state" in event.data && (
                          <Badge variant="outline">
                            {String(event.data.state)}
                          </Badge>
                        )}
                    </div>
                    {event.data &&
                      typeof event.data === "object" &&
                      "text" in event.data && (
                        <p className="text-sm truncate max-w-md">
                          {String(event.data.text)}
                        </p>
                      )}
                    {event.type === "meeting_booked" && (
                      <Badge className="w-fit bg-green-500">Booked</Badge>
                    )}
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
