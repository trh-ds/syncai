"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense } from "react";

import { AuthForm } from "@/components/AuthForm";

function SignupInner() {
  const params = useSearchParams();
  const plan = params.get("plan");
  const next = plan ? `/onboarding?plan=${encodeURIComponent(plan)}` : "/onboarding";

  return (
    <main className="mx-auto flex w-full max-w-md flex-1 flex-col items-center justify-center px-4 py-16">
      <h1 className="font-display text-3xl font-bold tracking-tight">Start free</h1>
      <p className="mt-2 text-sm text-muted-foreground">
        Create your account — connect your inbox in the next step.
      </p>
      <div className="mt-8 flex w-full justify-center">
        <AuthForm mode="signup" next={next} />
      </div>
      <p className="mt-6 text-sm text-muted-foreground">
        Already have an account?{" "}
        <Link href="/login" className="underline hover:text-foreground">
          Sign in
        </Link>
      </p>
    </main>
  );
}

export default function SignupPage() {
  return (
    <Suspense fallback={null}>
      <SignupInner />
    </Suspense>
  );
}
