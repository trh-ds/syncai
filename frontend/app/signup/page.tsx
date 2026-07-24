import Link from "next/link";

import { AuthForm } from "@/components/AuthForm";

export default function SignupPage() {
  return (
    <main className="mx-auto flex w-full max-w-md flex-1 flex-col items-center justify-center px-4 py-16">
      <h1 className="font-display text-3xl font-bold tracking-tight">Start free</h1>
      <p className="mt-2 text-sm text-muted-foreground">
        Create your account — connect your inbox in the next step.
      </p>
      <div className="mt-8 flex w-full justify-center">
        <AuthForm mode="signup" next="/onboarding" />
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
