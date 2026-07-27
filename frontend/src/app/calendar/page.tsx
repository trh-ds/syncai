"use client";

import { useEffect, useState, useCallback } from "react";
import { toast } from "sonner";
import { apiFetch } from "@/lib/api";
import { Calendar } from "@/components/ui/calendar";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { format } from "date-fns";

interface Meeting {
  id: string;
  title: string;
  start_at: string;
  end_at: string;
  status: string;
  lead_name: string | null;
  lead_email: string | null;
  hangout_link: string | null;
}

const STATUS_COLORS: Record<string, string> = {
  confirmed: "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300",
  booked: "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300",
  completed: "bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300",
  cancelled: "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300",
  no_show: "bg-gray-100 text-gray-800 dark:bg-gray-900/30 dark:text-gray-300",
};

export default function CalendarPage() {
  const [meetings, setMeetings] = useState<Meeting[]>([]);
  const [selectedDate, setSelectedDate] = useState<Date>(new Date());
  const [month, setMonth] = useState<Date>(new Date());
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        const data = await apiFetch<Meeting[]>("/api/meetings");
        if (!cancelled) {
          setMeetings(data);
          setError(null);
        }
      } catch (e) {
        if (!cancelled) {
          setError(e instanceof Error ? e.message : "Failed to load meetings");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    load();
    const interval = setInterval(load, 3000);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, []);

  const fetchMeetings = useCallback(async () => {
    try {
      const data = await apiFetch<Meeting[]>("/api/meetings");
      setMeetings(data);
    } catch {
      // keep existing data on polling error
    }
  }, []);

  const handleConfirm = async (id: string) => {
    try {
      await apiFetch(`/api/meetings/${id}/confirm`, { method: "POST" });
      toast.success("Meeting confirmed");
      fetchMeetings();
    } catch {
      toast.error("Failed to confirm meeting");
    }
  };

  const handleCancel = async (id: string) => {
    try {
      await apiFetch(`/api/meetings/${id}/cancel`, { method: "POST" });
      toast.success("Meeting cancelled");
      fetchMeetings();
    } catch {
      toast.error("Failed to cancel meeting");
    }
  };

  const selectedMeetings = meetings.filter((m) => {
    const start = new Date(m.start_at);
    return start.toDateString() === selectedDate.toDateString();
  });

  const meetingDates = meetings.map((m) => new Date(m.start_at));

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold tracking-tight">Calendar</h1>

      <div className="grid grid-cols-1 lg:grid-cols-[auto_1fr] gap-6">
        <Card>
          <CardContent className="pt-6">
            <Calendar
              mode="single"
              selected={selectedDate}
              onSelect={(d) => d && setSelectedDate(d)}
              month={month}
              onMonthChange={(d) => setMonth(d)}
              modifiers={{ hasMeeting: meetingDates }}
              modifiersClassNames={{
                hasMeeting: "font-bold underline decoration-blue-500 decoration-2 underline-offset-2",
              }}
            />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>
              {format(selectedDate, "EEEE, MMMM d, yyyy")}
            </CardTitle>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="space-y-3">
                {[1, 2, 3].map((i) => (
                  <Skeleton key={i} className="h-20 w-full" />
                ))}
              </div>
            ) : error ? (
              <p className="text-destructive">{error}</p>
            ) : selectedMeetings.length === 0 ? (
              <p className="text-muted-foreground text-sm">No meetings on this day</p>
            ) : (
              <div className="space-y-3">
                {selectedMeetings.map((meeting) => (
                  <div
                    key={meeting.id}
                    className="flex items-start justify-between rounded-lg border p-3"
                  >
                    <div className="space-y-1">
                      <p className="font-medium text-sm">{meeting.title}</p>
                      <p className="text-xs text-muted-foreground">
                        {format(new Date(meeting.start_at), "h:mm a")} –{" "}
                        {format(new Date(meeting.end_at), "h:mm a")}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        {meeting.lead_name ?? "—"}
                      </p>
                      {meeting.hangout_link && (
                        <a
                          href={meeting.hangout_link}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-xs text-blue-600 underline"
                        >
                          Join meeting
                        </a>
                      )}
                      <Badge
                        variant="outline"
                        className={STATUS_COLORS[meeting.status] ?? ""}
                      >
                        {meeting.status}
                      </Badge>
                    </div>
                    <div className="flex gap-1.5">
                      {meeting.status !== "confirmed" && (
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => handleConfirm(meeting.id)}
                        >
                          Confirm
                        </Button>
                      )}
                      {meeting.status !== "cancelled" && (
                        <Button
                          size="sm"
                          variant="outline"
                          className="text-destructive"
                          onClick={() => handleCancel(meeting.id)}
                        >
                          Cancel
                        </Button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
