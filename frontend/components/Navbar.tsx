import Link from "next/link";

export function Navbar() {
  return (
    <header className="border-b">
      <nav className="mx-auto flex h-14 max-w-6xl items-center gap-6 px-4">
        <Link href="/" className="font-semibold tracking-tight">
          ASDR
        </Link>
        <div className="flex gap-4 text-sm text-muted-foreground">
          <Link href="/dashboard" className="hover:text-foreground transition-colors">
            Inbox
          </Link>
          <Link href="/chat" className="hover:text-foreground transition-colors">
            Chat
          </Link>
          <Link href="/crm" className="hover:text-foreground transition-colors">
            CRM
          </Link>
          <Link href="/demo" className="hover:text-foreground transition-colors">
            Demo
          </Link>
        </div>
      </nav>
    </header>
  );
}
