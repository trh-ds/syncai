"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { apiFetch } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Mail, MessageCircle, Calendar, Phone, UserCheck } from "lucide-react";

interface LeadDetail {
  id: string;
  first_name: string;
  last_name: string;
  email: string;
  title: string;
  company: string;
  source: string;
  status: string;
  enrichment: Record<string, unknown> | null;
}

interface TimelineEvent {
  id: string;
  type: string;
  sub_type: string;
  timestamp: string;
  data: Record<string, unknown>;
}

const SOURCE_COLORS: Record<string, string> = {
  apollo: "bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300",
  inbound: "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300",
  sample: "bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-300",
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
  email_sent: <Mail className="size-4 text-blue-500" />,
  email_received: <Mail className="size-4 text-green-500" />,
  chat_message: <MessageCircle className="size-4 text-purple-500" />,
  meeting_booked: <Calendar className="size-4 text-green-500" />,
  meeting_cancelled: <Calendar className="size-4 text-red-500" />,
  call: <Phone className="size-4 text-orange-500" />,
  status_change: <UserCheck className="size-4 text-yellow-500" />,
};

export default function LeadDetailPage() {
  const params = useParams();
  const id = params.id as string;

  const [lead, setLead] = useState<LeadDetail | null>(null);
  const [timeline, setTimeline] = useState<TimelineEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        const [leadData, timelineData] = await Promise.all([
          apiFetch<LeadDetail>(`/api/leads/${id}`),
          apiFetch<TimelineEvent[]>(`/api/leads/${id}/timeline`),
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

  const sortedTimeline = [...timeline].sort(
    (a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
  );

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">
          {lead.first_name} {lead.last_name}
        </h1>
        <div className="flex flex-wrap items-center gap-2 mt-2 text-sm text-muted-foreground">
          <span>{lead.email}</span>
          <span>·</span>
          <span>{lead.company || "—"}</span>
          {lead.title && (
            <>
              <span>·</span>
              <span>{lead.title}</span>
            </>
          )}
          <Badge variant="outline" className={SOURCE_COLORS[lead.source] ?? ""}>
            {lead.source}
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
          {sortedTimeline.length === 0 ? (
            <p className="text-muted-foreground text-sm">No activity yet</p>
          ) : (
            <div className="space-y-0">
              {sortedTimeline.map((event) => (
                <div key={event.id} className="flex gap-3 py-3 border-b last:border-0">
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
                        {new Date(event.timestamp).toLocaleString()}
                      </span>
                    </div>
                    <p className="text-sm text-muted-foreground mt-0.5">
                      {event.sub_type}
                    </p>
                    {event.data && Object.keys(event.data).length > 0 && (
                      <p className="text-xs text-muted-foreground mt-1 truncate max-w-md">
                        {typeof event.data.text === "string"
                          ? event.data.text
                          : typeof event.data.subject === "string"
                            ? event.data.subject
                            : JSON.stringify(event.data).slice(0, 120)}
                      </p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </TabsContent>

        <TabsContent value="enrichment" className="mt-4">
          {lead.enrichment ? (
            <pre className="text-sm bg-muted rounded-lg p-4 overflow-auto max-h-96">
              {JSON.stringify(lead.enrichment, null, 2)}
            </pre>
          ) : (
            <p className="text-muted-foreground text-sm">No enrichment data</p>
          )}
        </TabsContent>

        <TabsContent value="emails" className="mt-4">
          {sortedTimeline.filter(
            (e) => e.type === "email_sent" || e.type === "email_received"
          ).length === 0 ? (
            <p className="text-muted-foreground text-sm">No emails yet</p>
          ) : (
            <div className="space-y-3">
              {sortedTimeline
                .filter(
                  (e) => e.type === "email_sent" || e.type === "email_received"
                )
                .map((event) => (
                  <div key={event.id} className="rounded-lg border p-3">
                    <div className="flex items-center gap-2 mb-1">
                      <span
                        className={`text-xs font-medium ${
                          event.type === "email_sent"
                            ? "text-blue-600"
                            : "text-green-600"
                        }`}
                      >
                        {event.type === "email_sent" ? "Sent" : "Received"}
                      </span>
                      <span className="text-xs text-muted-foreground">
                        {new Date(event.timestamp).toLocaleString()}
                      </span>
                    </div>
                    {event.data && typeof event.data === "object" && (
                      <>
                        {"subject" in event.data && (
                          <p className="text-sm font-medium">
                            {String(event.data.subject)}
                          </p>
                        )}
                        {"text" in event.data && (
                          <p className="text-xs text-muted-foreground mt-1 line-clamp-3">
                            {String(event.data.text)}
                          </p>
                        )}
                      </>
                    )}
                  </div>
                ))}
            </div>
          )}
        </TabsContent>

        <TabsContent value="chat" className="mt-4">
          {sortedTimeline.filter((e) => e.type === "chat_message").length ===
          0 ? (
            <p className="text-muted-foreground text-sm">No chat messages</p>
          ) : (
            <div className="space-y-3">
              {sortedTimeline
                .filter((e) => e.type === "chat_message")
                .reverse()
                .map((event) => {
                  const isInbound = event.sub_type === "inbound";
                  return (
                    <div
                      key={event.id}
                      className={`flex ${isInbound ? "justify-start" : "justify-end"}`}
                    >
                      <div
                        className={`max-w-[75%] rounded-lg px-3 py-2 text-sm ${
                          isInbound
                            ? "bg-muted"
                            : "bg-primary text-primary-foreground"
                        }`}
                      >
                        <p>
                          {event.data && typeof event.data === "object" && "text" in event.data
                            ? String(event.data.text)
                            : JSON.stringify(event.data)}
                        </p>
                        <span className="text-[10px] opacity-60 mt-1 block">
                          {new Date(event.timestamp).toLocaleTimeString()}
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
