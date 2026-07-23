"use client";

import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ApiError, getCrmActivity, getCrmStats, type CrmStats, type RecentActivityItem } from "@/lib/api";

function Bar({ label, value, total, color }: { label: string; value: number; total: number; color: string }) {
  const pct = Math.round((value / total) * 100);
  return (
    <div className="flex items-center gap-3">
      <span className="w-14 text-sm font-medium">{label}</span>
      <div className="flex-1 h-5 rounded-full bg-muted overflow-hidden">
        <div
          className={`h-full rounded-full transition-all ${color}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="w-10 text-right text-sm text-muted-foreground">{value}</span>
    </div>
  );
}

export default function CrmPage() {
  const [stats, setStats] = useState<CrmStats | null>(null);
  const [activity, setActivity] = useState<RecentActivityItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  function load() {
    setLoading(true);
    Promise.all([getCrmStats(), getCrmActivity()])
      .then(([s, a]) => {
        setStats(s);
        setActivity(a);
        setError(null);
      })
      .catch((e) => setError(e instanceof ApiError ? e.message : "Failed to load CRM data"))
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    let cancelled = false;
    getCrmStats()
      .then((s) => { if (!cancelled) setStats(s); })
      .catch((e) => { if (!cancelled) setError(e instanceof ApiError ? e.message : "Failed"); });
    getCrmActivity()
      .then((a) => { if (!cancelled) setActivity(a); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, []);

  const scoreTotal = stats ? stats.hot + stats.warm + stats.cold || 1 : 1;

  return (
    <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-8">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-semibold tracking-tight">CRM</h1>
        <Button variant="outline" size="sm" onClick={load}>
          Refresh
        </Button>
      </div>

      {loading ? (
        <p className="text-muted-foreground">Loading…</p>
      ) : error ? (
        <div className="rounded-md border border-destructive/50 bg-destructive/10 p-4 text-sm text-destructive">{error}</div>
      ) : stats ? (
        <>
          <div className="grid gap-4 md:grid-cols-4 mb-8">
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">Total Leads</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-2xl font-bold">{stats.total_leads}</p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">Booked Meetings</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-2xl font-bold">{stats.total_meetings}</p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">Conversion</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-2xl font-bold">
                  {stats.total_leads > 0 ? Math.round((stats.total_meetings / stats.total_leads) * 100) : 0}%
                </p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">Sources</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm">
                  {Object.entries(stats.by_source)
                    .map(([k, v]) => `${k}: ${v}`)
                    .join(" · ")}
                </p>
              </CardContent>
            </Card>
          </div>

          <div className="grid gap-6 md:grid-cols-2 mb-8">
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Lead Pipeline</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <Bar label="Hot" value={stats.hot} total={scoreTotal} color="bg-red-500" />
                <Bar label="Warm" value={stats.warm} total={scoreTotal} color="bg-yellow-500" />
                <Bar label="Cold" value={stats.cold} total={scoreTotal} color="bg-blue-500" />
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-base">Services Breakdown</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {Object.entries(stats.by_service)
                  .sort((a, b) => b[1] - a[1])
                  .map(([svc, count]) => (
                    <Bar
                      key={svc}
                      label={svc}
                      value={count}
                      total={Object.values(stats.by_service).reduce((a, b) => a + b, 0) || 1}
                      color="bg-green-500"
                    />
                  ))}
                {Object.keys(stats.by_service).length === 0 && (
                  <p className="text-sm text-muted-foreground">No service inquiries yet.</p>
                )}
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">Recent Activity</CardTitle>
            </CardHeader>
            <CardContent>
              {activity.length === 0 ? (
                <p className="text-sm text-muted-foreground">No activity yet.</p>
              ) : (
                <div className="space-y-2">
                  {activity.slice(0, 20).map((a, i) => (
                    <div key={i} className="flex items-center gap-3 text-sm">
                      <span
                        className={`rounded px-1.5 py-0.5 text-xs font-medium ${
                          a.type === "email"
                            ? "bg-blue-100 text-blue-700"
                            : a.type === "chat"
                              ? "bg-purple-100 text-purple-700"
                              : "bg-green-100 text-green-700"
                        }`}
                      >
                        {a.type}
                      </span>
                      <span className="flex-1 truncate">{a.description}</span>
                      <span className="text-xs text-muted-foreground">
                        {a.timestamp.slice(0, 16).replace("T", " ")}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </>
      ) : null}
    </main>
  );
}
