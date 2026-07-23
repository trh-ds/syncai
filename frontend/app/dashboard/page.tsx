"use client";

import { useCallback, useEffect, useState } from "react";

import { EmailCard } from "@/components/EmailCard";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ApiError, getSettings, listEmails, patchSettings, type Email, type EmailStatus, type MailMode, type Settings } from "@/lib/api";

const STATUSES: EmailStatus[] = ["pending", "approved", "discarded", "sent"];

export default function DashboardPage() {
  const [emails, setEmails] = useState<Email[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [settings, setSettings] = useState<Settings | null>(null);
  const [modeLoading, setModeLoading] = useState(false);

  const load = useCallback(() => {
    listEmails()
      .then((data) => {
        setEmails(data);
        setError(null);
      })
      .catch((e: unknown) => {
        setError(e instanceof ApiError ? e.message : "Failed to load emails");
      })
      .finally(() => setLoading(false));
  }, []);

  const loadSettings = useCallback(() => {
    getSettings()
      .then(setSettings)
      .catch(() => {}); // ponytail: settings fetch is best-effort, not critical
  }, []);

  useEffect(() => {
    load();
    loadSettings();
  }, [load, loadSettings]);

  function toggleMode() {
    if (!settings) return;
    const next: MailMode = settings.mail_mode === "auto" ? "hitl" : "auto";
    setModeLoading(true);
    patchSettings({ mail_mode: next })
      .then(setSettings)
      .catch((e) => setError(e instanceof ApiError ? e.message : "Failed to toggle mode"))
      .finally(() => setModeLoading(false));
  }

  return (
    <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-8">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-semibold tracking-tight">Inbox</h1>
        {settings && (
          <div className="flex items-center gap-3">
            {settings.gmail_configured ? (
              <span className="text-xs text-muted-foreground">
                {settings.gmail_user} &middot; polling every {settings.poll_interval}s
              </span>
            ) : (
              <span className="text-xs text-destructive">Gmail not configured</span>
            )}
            <button
              type="button"
              disabled={modeLoading}
              onClick={toggleMode}
              className="inline-flex h-8 items-center gap-2 rounded-md border px-3 text-xs font-medium transition-colors hover:bg-muted disabled:opacity-50 cursor-pointer"
            >
              <span
                className={`h-2 w-2 rounded-full ${
                  settings.mail_mode === "auto" ? "bg-green-500" : "bg-yellow-500"
                }`}
              />
              {settings.mail_mode === "auto" ? "Auto" : "HITL"}
            </button>
          </div>
        )}
      </div>

      {loading ? (
        <p className="text-muted-foreground">Loading emails…</p>
      ) : error ? (
        <div className="rounded-md border border-destructive/50 bg-destructive/10 p-4 text-sm text-destructive">
          {error}
        </div>
      ) : emails.length === 0 ? (
        <p className="text-muted-foreground">
          No emails yet. Inbound emails triaged by the AI will appear here.
        </p>
      ) : (
        <Tabs defaultValue="pending">
          <TabsList>
            {STATUSES.map((s) => (
              <TabsTrigger key={s} value={s} className="capitalize">
                {s} ({emails.filter((e) => e.status === s).length})
              </TabsTrigger>
            ))}
          </TabsList>
          {STATUSES.map((s) => (
            <TabsContent key={s} value={s}>
              {emails.filter((e) => e.status === s).length === 0 ? (
                <p className="text-sm text-muted-foreground">
                  No {s} emails.
                </p>
              ) : (
                <div className="grid gap-4 md:grid-cols-2">
                  {emails
                    .filter((e) => e.status === s)
                    .map((e) => (
                      <EmailCard key={e.id} email={e} onChanged={load} />
                    ))}
                </div>
              )}
            </TabsContent>
          ))}
        </Tabs>
      )}
    </main>
  );
}
