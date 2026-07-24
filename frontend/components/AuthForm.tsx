"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { getSupabase } from "@/lib/supabase";

export function AuthForm({ mode, next }: { mode: "signup" | "login"; next: string }) {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const sb = getSupabase();

  if (!sb) {
    return (
      <p className="text-sm text-muted-foreground">
        Auth is not configured. Set NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY.
      </p>
    );
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    setNotice(null);
    const client = getSupabase();
    if (!client) return;
    if (mode === "signup") {
      const { error } = await client.auth.signUp({ email, password });
      if (error) setError(error.message);
      else setNotice("Check your email to confirm your account, then sign in.");
    } else {
      const { error } = await client.auth.signInWithPassword({ email, password });
      if (error) setError(error.message);
      else router.push(next);
    }
    setBusy(false);
  }

  async function google() {
    const client = getSupabase();
    if (!client) return;
    await client.auth.signInWithOAuth({
      provider: "google",
      options: { redirectTo: `${window.location.origin}${next}` },
    });
  }

  return (
    <div className="w-full max-w-sm">
      <form onSubmit={submit} className="space-y-3">
        <input
          type="email"
          required
          placeholder="you@company.com"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className="w-full rounded-md border bg-white px-3 py-2 text-sm"
        />
        <input
          type="password"
          required
          minLength={6}
          placeholder="Password (6+ characters)"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="w-full rounded-md border bg-white px-3 py-2 text-sm"
        />
        <Button type="submit" className="w-full" disabled={busy}>
          {busy ? "…" : mode === "signup" ? "Create account" : "Sign in"}
        </Button>
      </form>
      <div className="my-4 flex items-center gap-3 text-xs text-muted-foreground">
        <span className="h-px flex-1 bg-border" />
        or
        <span className="h-px flex-1 bg-border" />
      </div>
      <Button variant="outline" className="w-full" onClick={google}>
        Continue with Google
      </Button>
      {error && <p className="mt-3 text-sm text-destructive">{error}</p>}
      {notice && <p className="mt-3 text-sm text-emerald-700">{notice}</p>}
    </div>
  );
}
