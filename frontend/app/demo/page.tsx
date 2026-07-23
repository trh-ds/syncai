"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { ApiError, runDemo, type DemoRunResponse } from "@/lib/api";

export default function DemoPage() {
  const [url, setUrl] = useState("");
  const [senderName, setSenderName] = useState("");
  const [emailBody, setEmailBody] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<DemoRunResponse | null>(null);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      setResult(
        await runDemo({ url, sender_name: senderName, email_body: emailBody }),
      );
    } catch (err) {
      setError(
        err instanceof ApiError && err.code === "SCRAPE_FAILED"
          ? "We couldn't read that URL. Check the address and try again."
          : err instanceof ApiError
            ? err.message
            : "Demo failed. Please try again.",
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="mx-auto w-full max-w-2xl flex-1 px-4 py-8">
      <h1 className="mb-2 text-2xl font-semibold tracking-tight">Live demo</h1>
      <p className="mb-6 text-sm text-muted-foreground">
        Paste your company URL and a sample inbound email. Watch the AI draft a
        personalized reply using your own website as context. Nothing is saved.
      </p>

      <Card>
        <CardContent className="pt-6">
          <form onSubmit={onSubmit} className="space-y-4">
            <div>
              <label htmlFor="url" className="mb-1 block text-sm font-medium">
                Company URL
              </label>
              <input
                id="url"
                type="url"
                required
                placeholder="https://yourcompany.com"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
              />
            </div>
            <div>
              <label htmlFor="sender" className="mb-1 block text-sm font-medium">
                Sender name
              </label>
              <input
                id="sender"
                type="text"
                required
                placeholder="John"
                value={senderName}
                onChange={(e) => setSenderName(e.target.value)}
                className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
              />
            </div>
            <div>
              <label htmlFor="body" className="mb-1 block text-sm font-medium">
                Sample inbound email
              </label>
              <Textarea
                id="body"
                required
                rows={5}
                placeholder="Do you offer SEO services?"
                value={emailBody}
                onChange={(e) => setEmailBody(e.target.value)}
              />
            </div>
            <Button type="submit" disabled={loading}>
              {loading ? "Drafting…" : "Run demo"}
            </Button>
          </form>
        </CardContent>
      </Card>

      {error && (
        <div className="mt-4 rounded-md border border-destructive/50 bg-destructive/10 p-4 text-sm text-destructive">
          {error}
        </div>
      )}

      {result && (
        <div className="mt-6 space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Drafted reply</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="whitespace-pre-wrap text-sm">{result.draft}</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Context used</CardTitle>
              <CardDescription>
                What the AI learned from your website
              </CardDescription>
            </CardHeader>
            <CardContent>
              <p className="whitespace-pre-wrap text-sm text-muted-foreground">
                {result.context_used}
              </p>
            </CardContent>
          </Card>
        </div>
      )}
    </main>
  );
}
