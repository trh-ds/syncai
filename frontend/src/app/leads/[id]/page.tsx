"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { apiFetch } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Mail, MessageCircle, Calendar, UserCheck } from "lucide-react";

interface LeadDetail {
  id: string;
  first_name: string | null;
  last_name: string | null;
  email: string;
  title: string | null;
  org_name: string | null;
  source: string;
  status: string;
  enriched_data: Record<string, unknown> | null;
}

interface TimelineEvent {
  type: string;
  created_at: string;
  payload: Record<string, unknown> | null;
}

interface TimelineResponse {
  lead: LeadDetail;
  events: TimelineEvent[];
  threads: Array<{
    id: string;
    subject: string;
    status: string;
    messages: Array<{
      id: string;
      direction: string;
      from_email: string | null;
      body_text: string | null;
      created_at: string | null;
    }>;
  }>;
  meetings: Array<{
    id: string;
    title: string;
    start_at: string | null;
    status: string;
    hangout_link: string | null;
  }>;
  chat_sessions: Array<{ id: string; state: string }>;
}

const SOURCE_COLORS: Record<string, string> = {
  apollo: "bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300",
  apollo_sample: "bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-300",
  email_inbound: "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300",
  chat: "bg-pink-100 text-pink-800 dark:bg-pink-900/30 dark:text-pink-300",
  manual: "bg-gray-100 text-gray-800 dark:bg-gray-900/30 dark:text-gray-300",
};

const SOURCE_LABELS: Record<string, string> = {
  apollo: "Apollo",
  apollo_sample: "Sample",
  email_inbound: "Inbound",
  chat: "Chat",
  manual: "Manual",
};

const STATUS_COLORS: Record<string, string> = {
  captured: "bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300",
  contacted: "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300",
  replied: "bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-300",
  booked: "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300",
  no_show: "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300",
  lost: "bg-gray-100 text-gray-800 dark:bg-gray-900/30 dark:text-gray-300",
};

const EVENT_ICONS: Record<string, React.ReactNode> = {
  email_inbound: <Mail className="size-4 text-green-500" />,
  email_outbound: <Mail className="size-4 text-blue-500" />,
  chat_inbound: <MessageCircle className="size-4 text-purple-500" />,
  chat_outbound: <MessageCircle className="size-4 text-pink-500" />,
  meeting: <Calendar className="size-4 text-green-500" />,
  meeting_booked: <Calendar className="size-4 text-green-500" />,
  lead_status_change: <UserCheck className="size-4 text-yellow-500" />,
};

export default function LeadDetailPage() {
  const params = useParams();
  const id = params.id as string;

  const [lead, setLead] = useState<LeadDetail | null>(null);
  const [timeline, setTimeline] = useState<TimelineResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        const [leadData, timelineData] = await Promise.all([
          apiFetch<LeadDetail>(`/api/leads/${id}`),
          apiFetch<TimelineResponse>(`/api/leads/${id}/timeline`),
        ]);
        if (!cancelled) {
          setLead(leadData);
          setTimeline(timelineData);
          setError(null);
        }
      } catch (e) {
        if (!cancelled) {
          setError(e instanceof Error ? e.message : "Failed to load lead");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    load();
    return () => { cancelled = true; };
  }, [id]);

  if (loading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-10 w-64" />
        <Skeleton className="h-6 w-96" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  if (error || !lead) {
    return (
      <div className="flex items-center justify-center h-64 text-destructive">
        {error ?? "Lead not found"}
      </div>
    );
  }

  const events = timeline?.events ?? [];
  const sortedEvents = [...events].sort(
    (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
  );

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">
          {lead.first_name ?? ""} {lead.last_name ?? ""}
        </h1>
        <div className="flex flex-wrap items-center gap-2 mt-2 text-sm text-muted-foreground">
          <span>{lead.email}</span>
          <span>·</span>
          <span>{lead.org_name ?? "—"}</span>
          {lead.title && (
            <>
              <span>·</span>
              <span>{lead.title}</span>
            </>
          )}
          <Badge variant="outline" className={SOURCE_COLORS[lead.source] ?? ""}>
            {SOURCE_LABELS[lead.source] ?? lead.source}
          </Badge>
          <Badge variant="outline" className={STATUS_COLORS[lead.status] ?? ""}>
            {lead.status}
          </Badge>
        </div>
      </div>

      <Tabs defaultValue="timeline">
        <TabsList variant="line">
          <TabsTrigger value="timeline">Timeline</TabsTrigger>
          <TabsTrigger value="enrichment">Enrichment</TabsTrigger>
          <TabsTrigger value="emails">Emails</TabsTrigger>
          <TabsTrigger value="chat">Chat</TabsTrigger>
        </TabsList>

        <TabsContent value="timeline" className="mt-4">
          {sortedEvents.length === 0 ? (
            <p className="text-muted-foreground text-sm">No activity yet</p>
          ) : (
            <div className="space-y-0">
              {sortedEvents.map((event, i) => {
                const p = event.payload ?? {};
                return (
                  <div key={i} className="flex gap-3 py-3 border-b last:border-0">
                    <div className="mt-0.5">
                      {EVENT_ICONS[event.type] ?? (
                        <div className="size-4 rounded-full bg-muted" />
                      )}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium capitalize">
                          {event.type.replace(/_/g, " ")}
                        </span>
                        <span className="text-xs text-muted-foreground">
                          {new Date(event.created_at).toLocaleString()}
                        </span>
                      </div>
                      {p && Object.keys(p).length > 0 && (
                        <p className="text-xs text-muted-foreground mt-1 truncate max-w-md">
                          {typeof p.subject === "string"
                            ? p.subject
                            : typeof p.text === "string"
                              ? p.text
                              : typeof p.title === "string"
                                ? p.title
                                : JSON.stringify(p).slice(0, 120)}
                        </p>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </TabsContent>

        <TabsContent value="enrichment" className="mt-4">
          {lead.enriched_data ? (
            <pre className="text-sm bg-muted rounded-lg p-4 overflow-auto max-h-96">
              {JSON.stringify(lead.enriched_data, null, 2)}
            </pre>
          ) : (
            <p className="text-muted-foreground text-sm">No enrichment data</p>
          )}
        </TabsContent>

        <TabsContent value="emails" className="mt-4">
          {sortedEvents.filter(
            (e) => e.type === "email_inbound" || e.type === "email_outbound"
          ).length === 0 ? (
            <p className="text-muted-foreground text-sm">No emails yet</p>
          ) : (
            <div className="space-y-3">
              {sortedEvents
                .filter((e) => e.type === "email_inbound" || e.type === "email_outbound")
                .map((event, i) => {
                  const p = event.payload ?? {};
                  return (
                    <div key={i} className="rounded-lg border p-3">
                      <div className="flex items-center gap-2 mb-1">
                        <span
                          className={`text-xs font-medium ${
                            event.type === "email_outbound" ? "text-blue-600" : "text-green-600"
                          }`}
                        >
                          {event.type === "email_outbound" ? "Sent" : "Received"}
                        </span>
                        <span className="text-xs text-muted-foreground">
                          {new Date(event.created_at).toLocaleString()}
                        </span>
                      </div>
                      {typeof p.subject === "string" && (
                        <p className="text-sm font-medium">{p.subject}</p>
                      )}
                      {typeof p.body_text === "string" && (
                        <p className="text-xs text-muted-foreground mt-1 line-clamp-3">
                          {p.body_text}
                        </p>
                      )}
                    </div>
                  );
                })}
            </div>
          )}
        </TabsContent>

        <TabsContent value="chat" className="mt-4">
          {sortedEvents.filter((e) => e.type.startsWith("chat_")).length === 0 ? (
            <p className="text-muted-foreground text-sm">No chat messages</p>
          ) : (
            <div className="space-y-3">
              {sortedEvents
                .filter((e) => e.type.startsWith("chat_"))
                .reverse()
                .map((event, i) => {
                  const p = event.payload ?? {};
                  const isInbound = event.type === "chat_inbound";
                  return (
                    <div
                      key={i}
                      className={`flex ${isInbound ? "justify-start" : "justify-end"}`}
                    >
                      <div
                        className={`max-w-[75%] rounded-lg px-3 py-2 text-sm ${
                          isInbound ? "bg-muted" : "bg-primary text-primary-foreground"
                        }`}
                      >
                        <p>{typeof p.text === "string" ? p.text : JSON.stringify(p)}</p>
                        <span className="text-[10px] opacity-60 mt-1 block">
                          {new Date(event.created_at).toLocaleTimeString()}
                        </span>
                      </div>
                    </div>
                  );
                })}
            </div>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}
