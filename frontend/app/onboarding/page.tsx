"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";

import { Button, buttonVariants } from "@/components/ui/button";
import {
  createCheckout,
  getGoogleConnectUrl,
  getOnboardingStatus,
  type OnboardingStatus,
} from "@/lib/api";
import { getSupabase } from "@/lib/supabase";

const PLANS = [
  { id: "starter", name: "Starter", price: "$49/mo" },
  { id: "growth", name: "Growth", price: "$149/mo" },
  { id: "scale", name: "Scale", price: "$399/mo" },
];

function OnboardingInner() {
  const params = useSearchParams();
  const wantedPlan = params.get("plan");
  const justConnected = params.get("connected") === "1";
  const billingDone = params.get("billing") === "success";

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
  }, [sb, justConnected, billingDone]);

  async function withToken(fn: (token: string) => Promise<void>) {
    if (!sb) return;
    setBusy(true);
    setError(null);
    const { data } = await sb.auth.getSession();
    if (!data.session) {
      window.location.assign("/login");
      return;
    }
    try {
      await fn(data.session.access_token);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Something went wrong");
    }
    setBusy(false);
  }

  const connectGmail = () =>
    withToken(async (token) => {
      const { auth_url } = await getGoogleConnectUrl(token);
      window.location.href = auth_url;
    });

  const checkout = (plan: string) =>
    withToken(async (token) => {
      const { checkout_url } = await createCheckout(token, plan);
      window.location.href = checkout_url;
    });

  const connected = status?.gmail_connected || justConnected;

  return (
    <main className="mx-auto w-full max-w-2xl flex-1 px-4 py-16">
      <h1 className="font-display text-3xl font-bold tracking-tight">Set up your workspace</h1>
      <p className="mt-2 text-muted-foreground">Two steps. Ten minutes. Then it runs itself.</p>

      {/* Step 1: plan */}
      <section className="mt-10 rounded-xl border bg-white p-6">
        <h2 className="font-semibold">
          1. Choose your plan{" "}
          {status && <span className="ml-2 text-sm font-normal text-muted-foreground">(current: {status.plan})</span>}
        </h2>
        {billingDone && (
          <p className="mt-2 text-sm text-emerald-700">Payment complete — your plan is active.</p>
        )}
        <div className="mt-4 grid gap-3 sm:grid-cols-3">
          {PLANS.map((p) => (
            <div key={p.id} className="rounded-lg border p-4">
              <p className="font-medium">{p.name}</p>
              <p className="text-sm text-muted-foreground">{p.price}</p>
              <Button
                size="sm"
                className="mt-3 w-full"
                variant={wantedPlan === p.id || status?.plan === p.id ? "default" : "outline"}
                disabled={busy || status?.plan === p.id}
                onClick={() => checkout(p.id)}
              >
                {status?.plan === p.id ? "Current" : `Choose ${p.name}`}
              </Button>
            </div>
          ))}
        </div>
        <p className="mt-3 text-xs text-muted-foreground">
          Test mode — use Stripe card 4242 4242 4242 4242. Starter works without payment.
        </p>
      </section>

      {/* Step 2: connect Gmail + Calendar */}
      <section className="mt-6 rounded-xl border bg-white p-6">
        <h2 className="font-semibold">2. Connect Gmail + Calendar</h2>
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
