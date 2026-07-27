"use client";

import { useEffect, useState, useRef, useCallback } from "react";
import { apiFetch } from "@/lib/api";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Send } from "lucide-react";

const DEMO_LEAD_ID =
  process.env.NEXT_PUBLIC_DEMO_LEAD_ID || "00000000-0000-0000-0000-000000000001";

interface ChatMessage {
  role: "user" | "assistant";
  text: string;
}

interface ChatResponse {
  reply: string;
  state: string;
  proposed_times?: string[];
  booked_meeting?: {
    hangout_link: string;
    start_at: string;
    end_at: string;
    title: string;
  } | null;
}

const STATE_LABELS: Record<string, string> = {
  GREETING: "Greeting",
  COLLECT_INFO: "Collecting Info",
  INTENT_CONFIRM: "Intent",
  PROPOSE_TIMES: "Proposing Times",
  CONFIRM: "Confirming",
  BOOK: "Booking",
  DONE: "Done",
  LOST: "Lost",
};

const STATE_COLORS: Record<string, string> = {
  GREETING: "bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300",
  COLLECT_INFO: "bg-indigo-100 text-indigo-800 dark:bg-indigo-900/30 dark:text-indigo-300",
  INTENT_CONFIRM: "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300",
  PROPOSE_TIMES: "bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-300",
  CONFIRM: "bg-pink-100 text-pink-800 dark:bg-pink-900/30 dark:text-pink-300",
  BOOK: "bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-300",
  DONE: "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300",
  LOST: "bg-gray-100 text-gray-800 dark:bg-gray-900/30 dark:text-gray-300",
};

export default function DemoChatPage() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [state, setState] = useState<string>("GREETING");
  const [proposedTimes, setProposedTimes] = useState<string[]>([]);
  const [bookedMeeting, setBookedMeeting] = useState<ChatResponse["booked_meeting"] | null>(null);
  const [sending, setSending] = useState(false);
  const initializedRef = useRef(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  const sendMessage = useCallback(
    async (text: string) => {
      setSending(true);
      const userMsg: ChatMessage = { role: "user", text };
      setMessages((prev) => [...prev, userMsg]);

      try {
        const res = await apiFetch<ChatResponse>("/api/chat/message", {
          method: "POST",
          body: JSON.stringify({ lead_id: DEMO_LEAD_ID, text }),
        });

        setMessages((prev) => [...prev, { role: "assistant", text: res.reply }]);
        setState(res.state);

        if (res.proposed_times) {
          setProposedTimes(res.proposed_times);
        }

        if (res.booked_meeting) {
          setBookedMeeting(res.booked_meeting);
          setProposedTimes([]);
        }
      } catch {
        setMessages((prev) => [
          ...prev,
          { role: "assistant", text: "Sorry, something went wrong. Please try again." },
        ]);
      } finally {
        setSending(false);
      }
    },
    []
  );

  useEffect(() => {
    if (!initializedRef.current) {
      initializedRef.current = true;
      sendMessage("Hi, I'm interested in a demo");
    }
  }, [sendMessage]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || sending || state === "DONE") return;
    sendMessage(input.trim());
    setInput("");
  };

  const handleProposedTime = (time: string) => {
    sendMessage(time);
    setProposedTimes([]);
  };

  const handleConfirm = (choice: "yes" | "no") => {
    sendMessage(choice);
  };

  return (
    <div className="max-w-2xl mx-auto space-y-4">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Demo Chat</h1>
        <p className="text-sm text-muted-foreground mt-1">
          AI Sales Development Rep conversation simulator
        </p>
      </div>

      <div className="flex items-center gap-2">
        <span className="text-sm text-muted-foreground">State:</span>
        <Badge
          variant="outline"
          className={STATE_COLORS[state] ?? ""}
        >
          {STATE_LABELS[state] ?? state}
        </Badge>
      </div>

      {bookedMeeting && (
        <Card className="border-green-300 dark:border-green-700 bg-green-50/50 dark:bg-green-950/20">
          <CardContent className="py-4 space-y-2">
            <p className="font-semibold text-green-700 dark:text-green-300 text-lg">
              Meeting Booked!
            </p>
            <p className="text-sm">
              <span className="font-medium">Link:</span>{" "}
              <a
                href={bookedMeeting.hangout_link}
                target="_blank"
                rel="noopener noreferrer"
                className="text-blue-600 underline"
              >
                {bookedMeeting.hangout_link}
              </a>
            </p>
            <p className="text-sm">
              <span className="font-medium">Time:</span>{" "}
              {new Date(bookedMeeting.start_at).toLocaleString()} –{" "}
              {new Date(bookedMeeting.end_at).toLocaleTimeString()}
            </p>
          </CardContent>
        </Card>
      )}

      <div className="rounded-xl border bg-card overflow-hidden">
        <div className="h-[500px] overflow-y-auto p-4 space-y-3">
          {messages.length === 0 && (
            <p className="text-center text-muted-foreground text-sm mt-8">
              Starting conversation...
            </p>
          )}
          {messages.map((msg, i) => (
            <div
              key={i}
              className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
            >
              <div
                className={`max-w-[80%] rounded-xl px-4 py-2.5 text-sm ${
                  msg.role === "user"
                    ? "bg-primary text-primary-foreground"
                    : "bg-muted"
                }`}
              >
                {msg.text}
              </div>
            </div>
          ))}

          {proposedTimes.length > 0 && state === "PROPOSE_TIMES" && (
            <div className="flex flex-col gap-2 ml-0">
              <p className="text-xs text-muted-foreground">
                Select a proposed time:
              </p>
              <div className="flex flex-wrap gap-2">
                {proposedTimes.map((time) => (
                  <Button
                    key={time}
                    variant="outline"
                    size="sm"
                    onClick={() => handleProposedTime(time)}
                  >
                    {new Date(time).toLocaleString()}
                  </Button>
                ))}
              </div>
            </div>
          )}

          {state === "CONFIRM" && bookedMeeting === null && (
            <div className="flex gap-2 ml-0">
              <Button
                variant="default"
                size="sm"
                onClick={() => handleConfirm("yes")}
              >
                Yes, confirm
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => handleConfirm("no")}
              >
                No, reschedule
              </Button>
            </div>
          )}

          <div ref={bottomRef} />
        </div>

        <form
          onSubmit={handleSubmit}
          className="flex items-center gap-2 border-t p-3"
        >
          <Input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={
              state === "DONE"
                ? "Meeting booked — conversation complete"
                : "Type your message..."
            }
            disabled={sending || state === "DONE"}
            className="flex-1"
          />
          <Button
            type="submit"
            disabled={sending || !input.trim() || state === "DONE"}
            size="icon"
          >
            <Send className="size-4" />
          </Button>
        </form>
      </div>
    </div>
  );
}
