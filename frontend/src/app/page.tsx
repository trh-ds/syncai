"use client";

import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Users,
  CalendarCheck,
  DollarSign,
  Clock,
} from "lucide-react";

interface Metrics {
  leads_captured: number;
  meetings_booked: number;
  meetings_booked_pct: number;
  est_cost_saved: number;
  est_hours_saved: number;
  avg_reply_latency_s: number;
  pipeline: {
    captured: number;
    contacted: number;
    replied: number;
    booked: number;
    no_show: number;
    lost: number;
  };
  activity_14d: { date: string; count: number }[];
}

const PIPELINE_COLORS: Record<string, string> = {
  captured: "bg-blue-500",
  contacted: "bg-yellow-500",
  replied: "bg-orange-500",
  booked: "bg-green-500",
  no_show: "bg-red-500",
  lost: "bg-gray-400",
};

const PIPELINE_LABELS: Record<string, string> = {
  captured: "Captured",
  contacted: "Contacted",
  replied: "Replied",
  booked: "Booked",
  no_show: "No Show",
  lost: "Lost",
};

export default function DashboardPage() {
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        const data = await apiFetch<Metrics>("/api/metrics");
        if (!cancelled) {
          setMetrics(data);
          setError(null);
        }
      } catch (e) {
        if (!cancelled) {
          setError(e instanceof Error ? e.message : "Failed to load metrics");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    load();
    const interval = setInterval(load, 5000);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, []);

  if (error) {
    return (
      <div className="flex items-center justify-center h-64 text-destructive">
        {error}
      </div>
    );
  }

  const totalPipeline = metrics
    ? Object.values(metrics.pipeline).reduce((a, b) => a + b, 0)
    : 0;

  const maxActivity = metrics
    ? Math.max(1, ...metrics.activity_14d.map((d) => d.count))
    : 1;

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold tracking-tight">Overview</h1>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {loading ? (
          <>
            {[1, 2, 3, 4].map((i) => (
              <Card key={i}>
                <CardContent className="pt-6 space-y-2">
                  <Skeleton className="h-4 w-24" />
                  <Skeleton className="h-8 w-16" />
                </CardContent>
              </Card>
            ))}
          </>
        ) : (
          <>
            <KpiCard
              title="Leads Captured"
              value={metrics?.leads_captured ?? 0}
              icon={<Users className="size-5 text-blue-500" />}
            />
            <KpiCard
              title="Meetings Booked"
              value={metrics?.meetings_booked ?? 0}
              suffix={
                metrics ? ` (${metrics.meetings_booked_pct}%)` : undefined
              }
              icon={<CalendarCheck className="size-5 text-green-500" />}
            />
            <KpiCard
              title="Est. Cost / Hours Saved"
              value={`$${metrics?.est_cost_saved ?? 0}`}
              suffix={metrics ? ` / ${metrics.est_hours_saved}h` : undefined}
              icon={<DollarSign className="size-5 text-emerald-500" />}
              valueClassName="text-lg"
            />
            <KpiCard
              title="Avg. Reply Latency"
              value={`${metrics?.avg_reply_latency_s ?? 0}s`}
              icon={<Clock className="size-5 text-purple-500" />}
            />
          </>
        )}
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Pipeline Status</CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <Skeleton className="h-8 w-full" />
          ) : totalPipeline === 0 ? (
            <p className="text-muted-foreground text-sm">No data</p>
          ) : (
            <div className="space-y-2">
              <div className="flex h-6 rounded-md overflow-hidden">
                {Object.entries(metrics!.pipeline).map(([key, count]) =>
                  count > 0 ? (
                    <div
                      key={key}
                      className={`${PIPELINE_COLORS[key]} h-full transition-all`}
                      style={{
                        width: `${(count / totalPipeline) * 100}%`,
                      }}
                      title={`${PIPELINE_LABELS[key]}: ${count}`}
                    />
                  ) : null
                )}
              </div>
              <div className="flex flex-wrap gap-3 text-xs text-muted-foreground">
                {Object.entries(metrics!.pipeline).map(([key, count]) => (
                  <span key={key} className="flex items-center gap-1.5">
                    <span
                      className={`inline-block size-2.5 rounded-sm ${PIPELINE_COLORS[key]}`}
                    />
                    {PIPELINE_LABELS[key]}: {count}
                  </span>
                ))}
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Activity (14 days)</CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="flex items-end gap-1 h-24">
              {Array.from({ length: 14 }).map((_, i) => (
                <Skeleton key={i} className="flex-1" style={{ height: `${20 + (i * 7) % 80}%` }} />
              ))}
            </div>
          ) : (
            <div className="flex items-end gap-1 h-24">
              {metrics!.activity_14d.map((day) => (
                <div
                  key={day.date}
                  className="flex-1 bg-blue-500 rounded-t-sm transition-all hover:bg-blue-600 min-h-[2px]"
                  style={{ height: `${(day.count / maxActivity) * 100}%` }}
                  title={`${day.date}: ${day.count} events`}
                />
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function KpiCard({
  title,
  value,
  suffix,
  icon,
  valueClassName,
}: {
  title: string;
  value: string | number;
  suffix?: string;
  icon: React.ReactNode;
  valueClassName?: string;
}) {
  return (
    <Card>
      <CardContent className="pt-6">
        <div className="flex items-center justify-between">
          <p className="text-sm text-muted-foreground">{title}</p>
          {icon}
        </div>
        <p className={`text-2xl font-semibold mt-1 ${valueClassName ?? ""}`}>
          {value}
          {suffix && (
            <span className="text-sm font-normal text-muted-foreground">
              {suffix}
            </span>
          )}
        </p>
      </CardContent>
    </Card>
  );
}
