"use client";

import { useEffect, useState, useCallback } from "react";
import { toast } from "sonner";
import { apiFetch } from "@/lib/api";
import { Calendar } from "@/components/ui/calendar";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { format, startOfDay } from "date-fns";

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

function sameDay(a: Date, b: Date) {
  return a.getFullYear() === b.getFullYear()
    && a.getMonth() === b.getMonth()
    && a.getDate() === b.getDate();
}

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
    return () => { cancelled = true; clearInterval(interval); };
  }, []);

  const fetchMeetings = useCallback(async () => {
    try {
      const data = await apiFetch<Meeting[]>("/api/meetings");
      setMeetings(data);
    } catch { /* keep existing on error */ }
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

  const scheduledMeetings = meetings.filter((m) => m.status !== "cancelled");
  const upcomingMeetings = scheduledMeetings
    .filter((m) => new Date(m.start_at) >= new Date())
    .sort((a, b) => new Date(a.start_at).getTime() - new Date(b.start_at).getTime());

  const selectedMeetings = meetings.filter((m) => {
    const start = new Date(m.start_at);
    return sameDay(start, selectedDate);
  });

  const meetingDays = meetings
    .filter((m) => m.status !== "cancelled")
    .map((m) => startOfDay(new Date(m.start_at)));

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
              modifiers={{ hasMeeting: meetingDays }}
              modifiersClassNames={{
                hasMeeting: "font-bold underline decoration-blue-500 decoration-2 underline-offset-2",
              }}
            />
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle>Upcoming Meetings</CardTitle>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="space-y-3">
                {[1, 2, 3].map((i) => <Skeleton key={i} className="h-20 w-full" />)}
              </div>
            ) : error ? (
              <p className="text-destructive">{error}</p>
            ) : upcomingMeetings.length === 0 ? (
              <p className="text-muted-foreground text-sm">No upcoming meetings</p>
            ) : (
              <div className="space-y-3">
                {upcomingMeetings.map((meeting) => (
                  <MeetingCard
                    key={meeting.id}
                    meeting={meeting}
                    onConfirm={handleConfirm}
                    onCancel={handleCancel}
                  />
                ))}
              </div>
            )}

            {selectedMeetings.length > 0 && (
              <>
                <CardTitle className="text-base mt-6 mb-3 border-t pt-4">
                  {format(selectedDate, "EEEE, MMMM d, yyyy")}
                </CardTitle>
                <div className="space-y-3">
                  {selectedMeetings.map((meeting) => (
                    <MeetingCard
                      key={meeting.id}
                      meeting={meeting}
                      onConfirm={handleConfirm}
                      onCancel={handleCancel}
                    />
                  ))}
                </div>
              </>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function MeetingCard({
  meeting,
  onConfirm,
  onCancel,
}: {
  meeting: Meeting;
  onConfirm: (id: string) => void;
  onCancel: (id: string) => void;
}) {
  const startDate = new Date(meeting.start_at);
  return (
    <div className="flex items-start justify-between rounded-lg border p-3">
      <div className="space-y-1">
        <div className="flex items-center gap-2">
          <span className="text-xs text-muted-foreground font-medium">
            {format(startDate, "MMM d, h:mm a")}
          </span>
          <Badge variant="outline" className={STATUS_COLORS[meeting.status] ?? ""}>
            {meeting.status}
          </Badge>
        </div>
        <p className="font-medium text-sm">{meeting.title}</p>
        {meeting.lead_name ? (
          <p className="text-xs text-muted-foreground">{meeting.lead_name}</p>
        ) : meeting.lead_email ? (
          <p className="text-xs text-muted-foreground">{meeting.lead_email}</p>
        ) : null}
      </div>
      <div className="flex gap-1.5">
        {meeting.status === "booked" && (
          <Button size="sm" variant="outline" onClick={() => onConfirm(meeting.id)}>
            Confirm
          </Button>
        )}
        {meeting.status !== "cancelled" && (
          <Button
            size="sm" variant="outline" className="text-destructive"
            onClick={() => onCancel(meeting.id)}
          >
            Cancel
          </Button>
        )}
      </div>
    </div>
  );
}
