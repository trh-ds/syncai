"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";

import { Button, buttonVariants } from "@/components/ui/button";
import { getGoogleConnectUrl, getOnboardingStatus, type OnboardingStatus } from "@/lib/api";
import { getSupabase } from "@/lib/supabase";

function OnboardingInner() {
  const params = useSearchParams();
  const justConnected = params.get("connected") === "1";

  const [status, setStatus] = useState<OnboardingStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const sb = getSupabase();

  useEffect(() => {
    if (!sb) return;
    let cancelled = false;
    sb.auth.getSession().then(({ data }) => {
      if (cancelled) return;
      if (!data.session) {
        window.location.assign("/login");
        return;
      }
      getOnboardingStatus(data.session.access_token)
        .then((s) => { if (!cancelled) setStatus(s); })
        .catch((e) => { if (!cancelled) setError(e.message); });
    });
    return () => { cancelled = true; };
  }, [sb, justConnected]);

  async function connectGmail() {
    if (!sb) return;
    setBusy(true);
    setError(null);
    const { data } = await sb.auth.getSession();
    if (!data.session) {
      window.location.assign("/login");
      return;
    }
    try {
      const { auth_url } = await getGoogleConnectUrl(data.session.access_token);
      window.location.href = auth_url;
    } catch (e) {
      setError(e instanceof Error ? e.message : "Something went wrong");
    }
    setBusy(false);
  }

  const connected = status?.gmail_connected || justConnected;

  return (
    <main className="mx-auto w-full max-w-xl flex-1 px-4 py-16">
      <h1 className="font-display text-3xl font-bold tracking-tight">Set up your workspace</h1>
      <p className="mt-2 text-muted-foreground">Connect your inbox. It does the rest.</p>

      <section className="mt-10 rounded-xl border bg-white p-6">
        <h2 className="font-semibold">Connect Gmail + Calendar</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          One Google sign-in gives ASDR permission to read your inbox, send replies, and book meetings.
        </p>
        {connected ? (
          <p className="mt-4 text-sm font-medium text-emerald-700">
            ✓ Connected{status?.gmail_user ? ` as ${status.gmail_user}` : ""}
          </p>
        ) : (
          <Button className="mt-4" disabled={busy} onClick={connectGmail}>
            Connect Google account
          </Button>
        )}
      </section>

      {error && <p className="mt-4 text-sm text-destructive">{error}</p>}

      <div className="mt-8">
        <Link href="/dashboard" className={buttonVariants({ variant: connected ? "default" : "outline" })}>
          {connected ? "Go to your inbox →" : "Skip for now"}
        </Link>
      </div>
    </main>
  );
}

export default function OnboardingPage() {
  return (
    <Suspense fallback={null}>
      <OnboardingInner />
    </Suspense>
  );
}
