// Typed fetch wrapper for the ASDR FastAPI backend.
// Shapes are the single source of truth from API_CONTRACTS.md.

const BASE_URL = process.env.NEXT_PUBLIC_API_URL;

export type EmailIntent = "Sales" | "Support" | "Spam" | "Other";
export type EmailStatus = "pending" | "approved" | "discarded" | "sent";
export type MailMode = "auto" | "hitl";

export interface Email {
  id: string;
  sender: string;
  sender_name: string | null;
  subject: string;
  body: string;
  intent: EmailIntent;
  summary: string;
  ai_draft: string | null;
  status: EmailStatus;
  created_at: string;
  updated_at: string;
}

export interface DemoRunRequest {
  url: string;
  sender_name: string;
  email_body: string;
}

export interface DemoRunResponse {
  draft: string;
  context_used: string;
}

// Contract error shape: { "error": { "code": "STRING", "message": "..." } }
export class ApiError extends Error {
  constructor(
    public code: string,
    message: string,
    public status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  if (!BASE_URL) {
    throw new ApiError(
      "CONFIG",
      "NEXT_PUBLIC_API_URL is not set. Copy .env.example to .env.local.",
      0,
    );
  }
  const res = await fetch(`${BASE_URL}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!res.ok) {
    let code = "HTTP_" + res.status;
    let message = res.statusText;
    try {
      const body: unknown = await res.json();
      if (
        typeof body === "object" &&
        body !== null &&
        "error" in body &&
        typeof (body as { error: unknown }).error === "object"
      ) {
        const err = (body as { error: { code?: unknown; message?: unknown } })
          .error;
        if (typeof err.code === "string") code = err.code;
        if (typeof err.message === "string") message = err.message;
      }
    } catch {
      // ponytail: non-JSON error body, fall back to HTTP status text
    }
    throw new ApiError(code, message, res.status);
  }
  return res.json() as Promise<T>;
}

export function listEmails(status?: EmailStatus): Promise<Email[]> {
  const qs = status ? `?status=${encodeURIComponent(status)}` : "";
  return request<Email[]>(`/api/v1/emails${qs}`);
}

export function getEmail(id: string): Promise<Email> {
  return request<Email>(`/api/v1/emails/${encodeURIComponent(id)}`);
}

export function patchEmail(
  id: string,
  patch: { ai_draft?: string; status?: EmailStatus },
): Promise<Email> {
  return request<Email>(`/api/v1/emails/${encodeURIComponent(id)}`, {
    method: "PATCH",
    body: JSON.stringify(patch),
  });
}

export function runDemo(input: DemoRunRequest): Promise<DemoRunResponse> {
  return request<DemoRunResponse>("/api/v1/demo/run", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export interface Settings {
  mail_mode: MailMode;
  poll_interval: number;
  gmail_configured: boolean;
  gmail_user: string;
}

export function getSettings(): Promise<Settings> {
  return request<Settings>("/api/v1/settings");
}

export function patchSettings(patch: {
  mail_mode: MailMode;
}): Promise<Settings> {
  return request<Settings>("/api/v1/settings", {
    method: "PATCH",
    body: JSON.stringify(patch),
  });
}

// ─── Chat ───

export interface ChatRequest {
  message: string;
  email?: string;
  name?: string;
}

export interface ChatResponse {
  reply: string;
  lead_score: string;
  customer_email: string | null;
  booking: { confirmed: boolean; start: string; end: string; summary: string } | null;
}

export function sendChat(input: ChatRequest): Promise<ChatResponse> {
  return request<ChatResponse>("/api/v1/chat/message", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

// ─── CRM ───

export interface CrmStats {
  total_leads: number;
  hot: number;
  warm: number;
  cold: number;
  total_meetings: number;
  pipeline_value: number;
  pipeline_forecast: number;
  by_source: Record<string, number>;
  by_service: Record<string, number>;
}

export interface RecentActivityItem {
  type: string;
  description: string;
  timestamp: string;
}

export function getCrmStats(): Promise<CrmStats> {
  return request<CrmStats>("/api/v1/crm/stats");
}

export function getCrmActivity(): Promise<RecentActivityItem[]> {
  return request<RecentActivityItem[]>("/api/v1/crm/activity");
}

// ─── Authenticated (Supabase JWT) ───

async function authedRequest<T>(path: string, token: string, init?: RequestInit): Promise<T> {
  if (!BASE_URL) {
    throw new ApiError("CONFIG", "NEXT_PUBLIC_API_URL is not set.", 0);
  }
  const res = await fetch(`${BASE_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
      ...init?.headers,
    },
  });
  if (!res.ok) {
    let message = res.statusText;
    try {
      const body = await res.json();
      if (body?.error?.message) message = body.error.message;
    } catch {
      // ponytail: non-JSON error body
    }
    throw new ApiError("HTTP_" + res.status, message, res.status);
  }
  return res.json() as Promise<T>;
}

export interface OnboardingStatus {
  gmail_connected: boolean;
  gmail_user: string | null;
}

export function getOnboardingStatus(token: string): Promise<OnboardingStatus> {
  return authedRequest<OnboardingStatus>("/api/v1/onboarding/status", token);
}

export function getGoogleConnectUrl(token: string): Promise<{ auth_url: string }> {
  return authedRequest<{ auth_url: string }>("/api/v1/onboarding/google", token);
}

export function unsubscribe(token: string): Promise<{ unsubscribed: boolean; email: string }> {
  return request<{ unsubscribed: boolean; email: string }>(`/api/v1/unsubscribe/${encodeURIComponent(token)}`, {
    method: "POST",
  });
}
