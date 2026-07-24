import Link from "next/link";

import { buttonVariants } from "@/components/ui/button";

const FEATURES = [
  {
    title: "Inbox Triage",
    body: "Every inbound email read, classified, and summarized in seconds. Spam dies silently. Real leads surface instantly.",
  },
  {
    title: "Drafted Replies",
    body: "Replies written from your own pricing, case studies, and policies — reviewed by you, or sent automatically.",
  },
  {
    title: "Chat That Closes",
    body: "A live assistant that answers questions, qualifies budget, and books meetings straight onto your calendar.",
  },
  {
    title: "Pipeline CRM",
    body: "Every lead scored hot, warm, or cold. See what's in the pipeline and what it's worth — no spreadsheets.",
  },
];

const STEPS = [
  { title: "Connect your inbox", body: "One OAuth click. We watch for new mail so you don't have to." },
  { title: "AI reads and replies", body: "Leads get a personal, on-brand reply in under a minute — with a link to keep talking." },
  { title: "Chat qualifies and books", body: "Your assistant answers questions, scores the lead, and drops a meeting on your calendar." },
  { title: "You just show up", body: "Approve anything you want, or let it run. One dashboard, zero chasing." },
];

const PRICING = [
  {
    name: "Starter",
    price: "$49",
    blurb: "For solo founders",
    items: ["1 inbox", "100 AI replies/mo", "Chat assistant", "Calendar booking", "Email support"],
  },
  {
    name: "Growth",
    price: "$149",
    blurb: "For small teams",
    items: ["3 inboxes", "500 AI replies/mo", "Lead scoring + CRM", "Slack alerts", "Priority support"],
    featured: true,
  },
  {
    name: "Scale",
    price: "$399",
    blurb: "For agencies",
    items: ["10 inboxes", "Unlimited replies", "Apollo enrichment", "Custom knowledge base", "Dedicated onboarding"],
  },
];

const FAQS = [
  {
    q: "Does it send emails without my approval?",
    a: "Your choice. Human-in-the-loop mode holds every draft for one-click approval. Auto mode sends instantly. Switch anytime from the dashboard.",
  },
  {
    q: "What does the chatbot do with my leads?",
    a: "It answers their questions using your knowledge base, qualifies them as hot, warm, or cold, and books meetings directly on your Google Calendar — checking for conflicts first.",
  },
  {
    q: "Is my data shared with other customers?",
    a: "No. Your inbox, leads, and knowledge base are scoped to your organization only.",
  },
  {
    q: "What happens if someone unsubscribes?",
    a: "They're flagged instantly and we never email them again. Every AI-drafted email includes a one-click unsubscribe link, per CAN-SPAM.",
  },
];

export default function Home() {
  return (
    <main className="flex-1">
      {/* ─── Hero ─── */}
      <section className="mx-auto w-full max-w-6xl px-4 pt-20 pb-16">
        <div className="grid items-center gap-12 md:grid-cols-2">
          <div>
            <p className="mb-4 inline-block rounded-full bg-blue-50 px-3 py-1 text-xs font-semibold tracking-wide text-blue-700">
              AI SALES OPS
            </p>
            <h1 className="font-display text-4xl font-bold leading-tight tracking-tight sm:text-5xl">
              A sales team you never have to manage.
            </h1>
            <p className="mt-5 max-w-md text-lg text-muted-foreground">
              Stop chasing replies and manually sorting leads. ASDR reads your
              inbox, drafts the reply, qualifies the lead, and books the
              meeting — before your coffee cools.
            </p>
            <div className="mt-8 flex gap-3">
              <Link href="/signup" className={buttonVariants({ size: "lg" })}>
                Start free
              </Link>
              <Link
                href="/demo"
                className={buttonVariants({ size: "lg", variant: "outline" })}
              >
                See it live
              </Link>
            </div>
          </div>

          {/* Signature: email-in → reply-out */}
          <div className="relative" aria-hidden="true">
            <div className="email-flow">
              <div className="email-card email-in">
                <p className="text-xs font-semibold text-blue-600">INBOUND · 0s</p>
                <p className="mt-1 text-sm font-medium">Need a quote for a website redesign</p>
                <p className="mt-1 text-xs text-muted-foreground">
                  Hi — our site is outdated and we&apos;re losing mobile customers…
                </p>
              </div>
              <div className="flow-pulse">
                <span className="flow-dot" />
                <span className="flow-dot" />
                <span className="flow-dot" />
              </div>
              <div className="email-card email-out">
                <p className="text-xs font-semibold text-emerald-600">DRAFTED · 4s</p>
                <p className="mt-1 text-sm font-medium">Re: Your redesign — $3K–$6.5K, 4–6 weeks</p>
                <p className="mt-1 text-xs text-muted-foreground">
                  Hi Sarah, great timing — mobile-first redesigns are exactly…
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ─── Problem / solution ─── */}
      <section className="border-t bg-white py-16">
        <div className="mx-auto max-w-3xl px-4 text-center">
          <h2 className="font-display text-3xl font-bold tracking-tight">
            Leads don&apos;t wait. Your inbox shouldn&apos;t either.
          </h2>
          <p className="mt-4 text-muted-foreground">
            The average lead goes cold in 5 minutes. Most small teams reply in
            5 hours — buried under newsletters, alerts, and spam. ASDR kills
            the busywork: it reads everything, ignores the noise, and answers
            the people who actually want to buy.
          </p>
        </div>
      </section>

      {/* ─── Feature grid ─── */}
      <section className="py-16">
        <div className="mx-auto max-w-6xl px-4">
          <h2 className="font-display text-center text-3xl font-bold tracking-tight">
            Four agents. Zero overhead.
          </h2>
          <div className="mt-10 grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
            {FEATURES.map((f) => (
              <div key={f.title} className="rounded-xl border bg-white p-6 shadow-sm">
                <h3 className="font-semibold">{f.title}</h3>
                <p className="mt-2 text-sm text-muted-foreground">{f.body}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ─── How it works ─── */}
      <section className="border-t bg-white py-16">
        <div className="mx-auto max-w-5xl px-4">
          <h2 className="font-display text-center text-3xl font-bold tracking-tight">
            Live in ten minutes
          </h2>
          <div className="mt-10 grid gap-8 sm:grid-cols-2 lg:grid-cols-4">
            {STEPS.map((s, i) => (
              <div key={s.title}>
                <div className="flex h-9 w-9 items-center justify-center rounded-full bg-blue-600 text-sm font-bold text-white">
                  {i + 1}
                </div>
                <h3 className="mt-3 font-semibold">{s.title}</h3>
                <p className="mt-1 text-sm text-muted-foreground">{s.body}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ─── Pricing ─── */}
      <section id="pricing" className="py-16">
        <div className="mx-auto max-w-5xl px-4">
          <h2 className="font-display text-center text-3xl font-bold tracking-tight">
            Cheaper than one hire
          </h2>
          <div className="mt-10 grid gap-6 md:grid-cols-3">
            {PRICING.map((t) => (
              <div
                key={t.name}
                className={`rounded-xl border p-6 shadow-sm ${
                  t.featured ? "border-blue-600 bg-white ring-1 ring-blue-600" : "bg-white"
                }`}
              >
                {t.featured && (
                  <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-blue-600">
                    Most popular
                  </p>
                )}
                <h3 className="text-lg font-semibold">{t.name}</h3>
                <p className="text-sm text-muted-foreground">{t.blurb}</p>
                <p className="mt-4">
                  <span className="font-display text-3xl font-bold">{t.price}</span>
                  <span className="text-sm text-muted-foreground">/mo</span>
                </p>
                <ul className="mt-4 space-y-2 text-sm">
                  {t.items.map((item) => (
                    <li key={item} className="flex gap-2">
                      <span className="text-emerald-600">✓</span>
                      {item}
                    </li>
                  ))}
                </ul>
                <Link
                  href={`/signup?plan=${t.name.toLowerCase()}`}
                  className={`${buttonVariants({ className: "mt-6 w-full", variant: t.featured ? "default" : "outline" })}`}
                >
                  Choose {t.name}
                </Link>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ─── FAQ ─── */}
      <section className="border-t bg-white py-16">
        <div className="mx-auto max-w-3xl px-4">
          <h2 className="font-display text-center text-3xl font-bold tracking-tight">FAQ</h2>
          <div className="mt-8 space-y-6">
            {FAQS.map((f) => (
              <div key={f.q}>
                <h3 className="font-semibold">{f.q}</h3>
                <p className="mt-1 text-sm text-muted-foreground">{f.a}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ─── Footer (compliance) ─── */}
      <footer className="border-t py-10">
        <div className="mx-auto flex max-w-6xl flex-col items-start justify-between gap-6 px-4 text-sm text-muted-foreground md:flex-row">
          <div>
            <p className="font-semibold text-foreground">Apex Digital LLC</p>
            <p>600 Congress Ave, Austin, TX 78701</p>
            <p className="mt-2">
              <a href="mailto:hello@apexdigital.com" className="underline hover:text-foreground">
                hello@apexdigital.com
              </a>
            </p>
          </div>
          <div className="flex flex-col gap-2">
            <Link href="/demo" className="hover:text-foreground">Live demo</Link>
            <a href="/unsubscribe" className="hover:text-foreground">
              Unsubscribe from emails
            </a>
            <p className="text-xs">
              We comply with CAN-SPAM. Every email we send includes your business identity and a working opt-out.
            </p>
          </div>
        </div>
      </footer>
    </main>
  );
}
