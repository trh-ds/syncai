import Link from "next/link";

import { AuthForm } from "@/components/AuthForm";

export default function LoginPage() {
  return (
    <main className="mx-auto flex w-full max-w-md flex-1 flex-col items-center justify-center px-4 py-16">
      <h1 className="font-display text-3xl font-bold tracking-tight">Welcome back</h1>
      <div className="mt-8 flex w-full justify-center">
        <AuthForm mode="login" next="/dashboard" />
      </div>
      <p className="mt-6 text-sm text-muted-foreground">
        No account?{" "}
        <Link href="/signup" className="underline hover:text-foreground">
          Start free
        </Link>
      </p>
    </main>
  );
}
