"use client";

import { useEffect, useState } from "react";
import { toast } from "sonner";
import { apiFetch } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { RefreshCw } from "lucide-react";

interface SyncStatus {
  last_sync_at: string | null;
  syncing: boolean;
  synced_count: number | null;
}

export default function ApolloSettingsPage() {
  const [status, setStatus] = useState<SyncStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        const data = await apiFetch<SyncStatus>("/api/leads/sync-apollo/status");
        if (!cancelled) setStatus(data);
      } catch {
        // best-effort
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    load();
    return () => { cancelled = true; };
  }, []);

  useEffect(() => {
    if (!syncing) return;
    const interval = setInterval(async () => {
      try {
        const data = await apiFetch<SyncStatus>(
          "/api/leads/sync-apollo/status"
        );
        setStatus(data);
        if (!data.syncing) {
          setSyncing(false);
          toast.success(
            `Sync completed: ${data.synced_count ?? 0} leads synced`
          );
        }
      } catch {
        // keep polling
      }
    }, 2000);
    return () => clearInterval(interval);
  }, [syncing]);

  const handleSync = async () => {
    setSyncing(true);
    try {
      await apiFetch("/api/leads/sync-apollo", { method: "POST" });
    } catch {
      setSyncing(false);
      toast.error("Sync failed");
    }
  };

  return (
    <div className="space-y-6 max-w-lg">
      <h1 className="text-2xl font-semibold tracking-tight">Apollo Settings</h1>

      <Card>
        <CardHeader>
          <CardTitle>Sync Status</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {loading ? (
            <Skeleton className="h-20 w-full" />
          ) : (
            <>
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">Last Sync</span>
                <span>
                  {status?.last_sync_at
                    ? new Date(status.last_sync_at).toLocaleString()
                    : "Never"}
                </span>
              </div>
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">Status</span>
                <span
                  className={
                    syncing || status?.syncing
                      ? "text-yellow-600 font-medium"
                      : "text-green-600 font-medium"
                  }
                >
                  {syncing || status?.syncing ? "Syncing..." : "Idle"}
                </span>
              </div>
              {status?.synced_count != null && (
                <div className="flex items-center justify-between text-sm">
                  <span className="text-muted-foreground">Leads Synced</span>
                  <span className="font-medium">{status.synced_count}</span>
                </div>
              )}
              {(syncing || status?.syncing) && (
                <div className="w-full bg-muted rounded-full h-2 overflow-hidden">
                  <div className="bg-blue-500 h-full rounded-full animate-pulse w-2/3" />
                </div>
              )}
            </>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Actions</CardTitle>
        </CardHeader>
        <CardContent>
          <Button
            onClick={handleSync}
            disabled={syncing || status?.syncing}
            className="w-full"
          >
            <RefreshCw
              className={`size-4 ${syncing || status?.syncing ? "animate-spin" : ""}`}
            />
            {syncing || status?.syncing ? "Syncing..." : "Sync Now"}
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
