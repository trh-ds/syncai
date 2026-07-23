"use client";

import { useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { ApiError, patchEmail, type Email, type EmailIntent } from "@/lib/api";

const intentVariant: Record<EmailIntent, "default" | "secondary" | "destructive" | "outline"> = {
  Sales: "default",
  Support: "secondary",
  Spam: "destructive",
  Other: "outline",
};

export function EmailCard({
  email,
  onChanged,
}: {
  email: Email;
  onChanged: () => void;
}) {
  const [draft, setDraft] = useState(email.ai_draft ?? "");
  const [showBody, setShowBody] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const draftEdited = email.ai_draft !== null && draft !== email.ai_draft;

  async function mutate(patch: { ai_draft?: string; status?: Email["status"] }) {
    setBusy(true);
    setError(null);
    try {
      await patchEmail(email.id, patch);
      onChanged();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Request failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0">
            <CardTitle className="truncate text-base">{email.subject}</CardTitle>
            <p className="mt-1 truncate text-sm text-muted-foreground">
              {email.sender_name ? `${email.sender_name} ` : ""}
              &lt;{email.sender}&gt;
            </p>
          </div>
          <Badge variant={intentVariant[email.intent]}>{email.intent}</Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-3 pb-3">
        <p className="text-sm text-muted-foreground">{email.summary}</p>

        <div>
          <button
            type="button"
            onClick={() => setShowBody((v) => !v)}
            className="text-xs font-medium text-muted-foreground underline-offset-4 hover:underline cursor-pointer"
          >
            {showBody ? "Hide original email" : "Show original email"}
          </button>
          {showBody && (
            <p className="mt-2 whitespace-pre-wrap rounded-md bg-muted p-3 text-sm">
              {email.body}
            </p>
          )}
        </div>

        {email.ai_draft !== null && (
          <div>
            <label className="mb-1 block text-xs font-medium text-muted-foreground">
              AI draft
            </label>
            <Textarea
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              rows={7}
            />
          </div>
        )}

        {error && <p className="text-sm text-destructive">{error}</p>}
      </CardContent>

      {email.status === "pending" && (
        <CardFooter className="gap-2">
          {email.ai_draft !== null && (
            <Button
              size="sm"
              disabled={busy}
              onClick={() =>
                mutate(draftEdited ? { ai_draft: draft, status: "approved" } : { status: "approved" })
              }
            >
              Approve &amp; Send
            </Button>
          )}
          <Button
            size="sm"
            variant="outline"
            disabled={busy}
            onClick={() => mutate({ status: "discarded" })}
          >
            Discard
          </Button>
          {email.ai_draft !== null && draftEdited && (
            <Button
              size="sm"
              variant="secondary"
              disabled={busy}
              onClick={() => mutate({ ai_draft: draft })}
            >
              Save draft
            </Button>
          )}
        </CardFooter>
      )}
      {email.status === "sent" && (
        <CardFooter>
          <span className="text-xs text-muted-foreground">
            Sent automatically via Gmail
          </span>
        </CardFooter>
      )}
    </Card>
  );
}
