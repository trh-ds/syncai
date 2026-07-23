import Link from "next/link";

import { buttonVariants } from "@/components/ui/button";

export default function Home() {
  return (
    <main className="mx-auto flex w-full max-w-3xl flex-1 flex-col items-center justify-center px-4 py-24 text-center">
      <h1 className="text-4xl font-semibold tracking-tight sm:text-5xl">
        Autonomous SDR &amp; Ops Router
      </h1>
      <p className="mt-4 max-w-xl text-muted-foreground">
        AI that triages your inbound email, qualifies leads, and drafts
        personalized replies in seconds — ready for one-click approval.
      </p>
      <div className="mt-8 flex gap-3">
        <Link href="/dashboard" className={buttonVariants({ size: "lg" })}>
          Open dashboard
        </Link>
        <Link
          href="/demo"
          className={buttonVariants({ size: "lg", variant: "outline" })}
        >
          Try the live demo
        </Link>
      </div>
    </main>
  );
}
