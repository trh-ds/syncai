export default function UnsubscribePage() {
  return (
    <main className="mx-auto w-full max-w-xl flex-1 px-4 py-16">
      <h1 className="font-display text-3xl font-bold tracking-tight">Unsubscribe</h1>
      <p className="mt-4 text-muted-foreground">
        Every email we send contains a one-click unsubscribe link in its footer.
        Click that link and you will be removed instantly — no login, no questions.
      </p>
      <p className="mt-4 text-muted-foreground">
        Can&apos;t find it? Email us at{" "}
        <a href="mailto:hello@apexdigital.com" className="underline hover:text-foreground">
          hello@apexdigital.com
        </a>{" "}
        with the subject &quot;unsubscribe&quot; and we&apos;ll remove you within 10 business days,
        per CAN-SPAM.
      </p>
      <p className="mt-8 text-sm text-muted-foreground">
        Apex Digital LLC · 600 Congress Ave, Austin, TX 78701
      </p>
    </main>
  );
}
