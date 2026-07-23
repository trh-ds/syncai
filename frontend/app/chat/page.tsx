"use client";

import { useEffect, useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { ApiError, sendChat, type ChatResponse } from "@/lib/api";

interface Message {
  role: "user" | "bot";
  text: string;
  leadScore?: string;
  booking?: ChatResponse["booking"];
}

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [emailSet, setEmailSet] = useState(false);
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function send(msg: string) {
    if (!msg.trim()) return;
    const userMsg: Message = { role: "user", text: msg };
    setMessages((p) => [...p, userMsg]);
    setInput("");
    setLoading(true);

    try {
      const res = await sendChat({
        message: msg,
        email: emailSet ? email : undefined,
        name: emailSet ? name : undefined,
      });
      const botMsg: Message = {
        role: "bot",
        text: res.reply,
        leadScore: res.lead_score,
        booking: res.booking || undefined,
      };
      setMessages((p) => [...p, botMsg]);
    } catch (e) {
      setMessages((p) => [
        ...p,
        { role: "bot", text: e instanceof ApiError ? e.message : "Something went wrong. Try again." },
      ]);
    } finally {
      setLoading(false);
    }
  }

  function handleSetEmail() {
    if (email.trim()) setEmailSet(true);
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    send(input);
  }

  return (
    <main className="mx-auto flex w-full max-w-2xl flex-1 flex-col px-4 py-6">
      <h1 className="mb-1 text-2xl font-semibold tracking-tight">Sales Assistant</h1>
      <p className="mb-6 text-sm text-muted-foreground">
        Chat with our AI to learn about our services, get pricing, or book a meeting.
      </p>

      {!emailSet ? (
        <div className="rounded-lg border p-6 space-y-4">
          <p className="text-sm text-muted-foreground">Let us know who you are so we can help you better.</p>
          <div>
            <label className="mb-1 block text-sm font-medium">Name</label>
            <input
              type="text"
              placeholder="John"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
            />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium">Email</label>
            <input
              type="email"
              placeholder="john@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
            />
          </div>
          <Button onClick={handleSetEmail} disabled={!email.trim()}>
            Start chatting
          </Button>
        </div>
      ) : (
        <>
          <div className="flex-1 space-y-4 overflow-y-auto rounded-lg border p-4 mb-4 min-h-0" style={{ maxHeight: "60vh" }}>
            {messages.length === 0 && (
              <p className="text-center text-sm text-muted-foreground py-8">
                Hi{name ? ` ${name}` : ""}! How can I help you today?
              </p>
            )}
            {messages.map((m, i) => (
              <div key={i} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
                <div
                  className={`max-w-[80%] rounded-lg px-4 py-2 text-sm ${
                    m.role === "user"
                      ? "bg-primary text-primary-foreground"
                      : "bg-muted"
                  }`}
                >
                  <p className="whitespace-pre-wrap">{m.text}</p>
                  {m.leadScore && (
                    <span
                      className={`mt-1 inline-block rounded-full px-2 py-0.5 text-xs font-medium ${
                        m.leadScore === "hot"
                          ? "bg-red-100 text-red-700"
                          : m.leadScore === "warm"
                            ? "bg-yellow-100 text-yellow-700"
                            : "bg-blue-100 text-blue-700"
                      }`}
                    >
                      {m.leadScore}
                    </span>
                  )}
                  {m.booking?.confirmed && (
                    <div className="mt-2 rounded bg-green-50 p-2 text-xs text-green-700">
                      Meeting booked: {m.booking.start?.slice(0, 16)}
                    </div>
                  )}
                </div>
              </div>
            ))}
            {loading && (
              <div className="flex justify-start">
                <div className="max-w-[80%] rounded-lg bg-muted px-4 py-2 text-sm text-muted-foreground">
                  Typing…
                </div>
              </div>
            )}
            <div ref={bottomRef} />
          </div>

          <form onSubmit={handleSubmit} className="flex gap-2">
            <input
              type="text"
              placeholder="Type your message…"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              disabled={loading}
              className="flex h-9 flex-1 rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:opacity-50"
            />
            <Button type="submit" disabled={loading || !input.trim()}>
              Send
            </Button>
          </form>
        </>
      )}
    </main>
  );
}
