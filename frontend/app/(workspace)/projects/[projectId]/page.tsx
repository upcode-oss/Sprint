"use client";

import { CalendarDays, Clock, FileText, ListChecks, SlidersHorizontal, Users } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { useAuth } from "@/features/auth/auth-context";

import { Badge } from "@/components/ui/badge";
import { Card, CardHeader } from "@/components/ui/card";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/states";
import { useProject } from "@/features/projects/project-context";
import { useResource } from "@/hooks/use-resource";
import { formatDate, formatDuration } from "@/lib/utils";
import type { ProjectOverview } from "@/types/api";

const overviewCards = [
  ["task-count", "Current tasks (count)"],
  ["tracked-time", "Tracked time"],
  ["active-sprint", "Active sprint"],
  ["members", "Members"],
  ["meeting-count", "Upcoming meetings (count)"],
  ["tracked-tasks", "Tracked time by ticket"],
  ["tasks", "Current tasks (list)"],
  ["meetings", "Upcoming meetings (list)"],
  ["documents", "Recent document changes"],
] as const;
type CardId = (typeof overviewCards)[number][0];

export default function ProjectOverviewPage() {
  const { project } = useProject();
  const { user } = useAuth();
  const storageKey = `sprint:overview:v1:${user.id}:${project.id}`;
  return <ProjectOverviewContent key={storageKey} storageKey={storageKey} />;
}

function ProjectOverviewContent({ storageKey }: { storageKey: string }) {
  const [hiddenCards, setHiddenCards] = useState<CardId[]>([]);
  const [customizing, setCustomizing] = useState(false);
  const [storageWarning, setStorageWarning] = useState(false);
  useEffect(() => {
    try {
      const saved: unknown = JSON.parse(localStorage.getItem(storageKey) ?? "[]");
      if (Array.isArray(saved)) {
        setHiddenCards(overviewCards.map(([id]) => id).filter((id) => saved.includes(id)));
      }
    } catch {
      // Unavailable or invalid saved preferences leave all cards visible.
    }
  }, [storageKey]);

  function updateHiddenCards(next: CardId[]) {
    setHiddenCards(next);
    try {
      localStorage.setItem(storageKey, JSON.stringify(next));
      setStorageWarning(false);
    } catch {
      setStorageWarning(true);
    }
  }
  const visible = (id: CardId) => !hiddenCards.includes(id);

  const { project } = useProject();
  const { data, error, loading, reload } = useResource<ProjectOverview>(
    `/projects/${project.id}/overview`,
  );
  if (loading) return <LoadingState />;
  if (error || !data)
    return <ErrorState message={error ?? "Overview unavailable"} retry={reload} />;
  return (
    <>
      <div className="toolbar" style={{ justifyContent: "flex-end" }}>
        <Button variant="outline" onClick={() => setCustomizing(true)}>
          <SlidersHorizontal aria-hidden />
          Customize overview
        </Button>
      </div>
      <Dialog
        open={customizing}
        onOpenChange={setCustomizing}
        title="Customize overview"
        description="Choose which cards appear. Your selection is saved for this project in this browser."
      >
        <div className="stack">
          {overviewCards.map(([id, label]) => (
            <label
              key={id}
              style={{ display: "flex", alignItems: "center", gap: ".75rem", cursor: "pointer" }}
            >
              <input
                type="checkbox"
                checked={visible(id)}
                onChange={(event) =>
                  updateHiddenCards(
                    event.target.checked
                      ? hiddenCards.filter((card) => card !== id)
                      : [...hiddenCards, id],
                  )
                }
              />
              {label}
            </label>
          ))}
        </div>
        {storageWarning && (
          <p role="status" className="muted small">
            Your browser could not save this selection. It will only apply until you leave this
            page.
          </p>
        )}
        <div className="dialog-actions">
          <Button variant="outline" onClick={() => updateHiddenCards([])}>
            Show all cards
          </Button>
          <Button onClick={() => setCustomizing(false)}>Done</Button>
        </div>
      </Dialog>
      {hiddenCards.length === overviewCards.length && (
        <EmptyState
          title="All cards are hidden"
          description="Use Customize overview to show cards again."
        />
      )}
      {overviewCards.slice(0, 5).some(([id]) => visible(id)) && (
        <div className="metrics-grid">
          {visible("task-count") && (
            <Card className="metric">
              <span className="metric-label">Current tasks</span>
              <strong className="metric-value">{data.tasks.length}</strong>
              <span className="metric-icon">
                <ListChecks />
              </span>
            </Card>
          )}
          {visible("tracked-time") && (
            <Card className="metric">
              <span className="metric-label">Tracked time</span>
              <strong className="metric-value">{formatDuration(data.total_tracked_seconds)}</strong>
              <span className="metric-icon">
                <Clock />
              </span>
            </Card>
          )}
          {visible("active-sprint") && (
            <Card className="metric">
              <span className="metric-label">Active sprint</span>
              <strong className="metric-value" style={{ fontSize: "1.15rem" }}>
                {data.active_sprint?.name ?? "None"}
              </strong>
              <span className="metric-icon">
                <ListChecks />
              </span>
            </Card>
          )}
          {visible("members") && (
            <Card className="metric">
              <span className="metric-label">Members</span>
              <strong className="metric-value">{data.member_count}</strong>
              <span className="metric-icon">
                <Users />
              </span>
            </Card>
          )}
          {visible("meeting-count") && (
            <Card className="metric">
              <span className="metric-label">Upcoming meetings</span>
              <strong className="metric-value">{data.upcoming_meetings.length}</strong>
              <span className="metric-icon">
                <CalendarDays />
              </span>
            </Card>
          )}
        </div>
      )}
      {overviewCards.slice(5).some(([id]) => visible(id)) && (
        <div className="content-grid">
          {visible("tracked-tasks") && (
            <Card className="wide">
              <CardHeader
                title="Tracked time by ticket"
                description="All tickets with recorded time, sorted by duration."
                action={<Clock />}
              />
              {data.tracked_tasks.length ? (
                <div className="table-wrap">
                  <table>
                    <thead>
                      <tr>
                        <th>Ticket</th>
                        <th>Status</th>
                        <th>Tracked time</th>
                      </tr>
                    </thead>
                    <tbody>
                      {data.tracked_tasks.map((task) => (
                        <tr key={task.id}>
                          <td>
                            <Link href={`/projects/${project.id}/kanban`}>
                              <span className="mono small muted">{task.reference}</span>
                              <strong className="tracked-time-ticket-title">{task.title}</strong>
                            </Link>
                          </td>
                          <td>
                            <Badge>{task.status.replaceAll("_", " ")}</Badge>
                          </td>
                          <td className="mono">
                            <strong>{formatDuration(task.tracked_seconds)}</strong>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                    <tfoot>
                      <tr>
                        <td colSpan={2}>
                          <strong>Total</strong>
                        </td>
                        <td className="mono">
                          <strong>{formatDuration(data.total_tracked_seconds)}</strong>
                        </td>
                      </tr>
                    </tfoot>
                  </table>
                </div>
              ) : (
                <EmptyState
                  title="No tracked time"
                  description="Add hours, minutes or seconds to a ticket to see it here."
                />
              )}
            </Card>
          )}
          {visible("tasks") && (
            <Card>
              <CardHeader title="Current tasks" />
              {data.tasks.length ? (
                <div className="stack">
                  {data.tasks.map((task) => (
                    <Link href={`/projects/${project.id}/kanban`} className="split" key={task.id}>
                      <div>
                        <span className="mono small muted">{task.reference}</span>
                        <div>{task.title}</div>
                      </div>
                      <Badge>{task.status.replaceAll("_", " ")}</Badge>
                    </Link>
                  ))}
                </div>
              ) : (
                <EmptyState
                  title="No tasks"
                  description="Create the first task on the Kanban board."
                />
              )}
            </Card>
          )}
          {visible("meetings") && (
            <Card>
              <CardHeader title="Upcoming meetings" />
              {data.upcoming_meetings.length ? (
                <div className="stack">
                  {data.upcoming_meetings.map((meeting) => (
                    <div key={meeting.id}>
                      <strong>{meeting.title}</strong>
                      <div className="muted small">{formatDate(meeting.start, true)}</div>
                    </div>
                  ))}
                </div>
              ) : (
                <EmptyState
                  title="No meetings"
                  description="Schedule a project meeting when needed."
                />
              )}
            </Card>
          )}
          {visible("documents") && (
            <Card className="wide">
              <CardHeader title="Recent document changes" action={<FileText />} />
              {data.recent_documents.length ? (
                <div className="stack">
                  {data.recent_documents.map((document) => (
                    <Link
                      href={`/projects/${project.id}/documents`}
                      className="split"
                      key={document.id}
                    >
                      <strong>{document.title}</strong>
                      <span className="muted small">{formatDate(document.updated_at, true)}</span>
                    </Link>
                  ))}
                </div>
              ) : (
                <EmptyState
                  title="No documents"
                  description="Project knowledge will appear here."
                />
              )}
            </Card>
          )}
        </div>
      )}
    </>
  );
}
