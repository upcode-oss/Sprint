"use client";

import { CalendarDays, FolderKanban, ListChecks, Users } from "lucide-react";
import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { Card, CardHeader } from "@/components/ui/card";
import { ErrorState, LoadingState, EmptyState } from "@/components/ui/states";
import { PageHeader } from "@/components/page-header";
import { useAuth } from "@/features/auth/auth-context";
import { useResource } from "@/hooks/use-resource";
import { formatDate } from "@/lib/utils";
import type { PersonalDashboard } from "@/types/api";

export default function DashboardPage() {
  const { user } = useAuth(); const { data, error, loading, reload } = useResource<PersonalDashboard>("/dashboard");
  if (loading) return <LoadingState label="Loading your dashboard…" />;
  if (error || !data) return <ErrorState message={error ?? "Dashboard unavailable"} retry={reload} />;
  return <>
    <PageHeader title={`Good to see you, ${user.first_name}`} description="Everything that needs your attention across your workspace." />
    <div className="metrics-grid">
      <Card className="metric"><span className="metric-label">My open tasks</span><strong className="metric-value">{data.tasks.length}</strong><span className="metric-icon"><ListChecks /></span></Card>
      <Card className="metric"><span className="metric-label">Active sprints</span><strong className="metric-value">{data.active_sprints.length}</strong><span className="metric-icon"><FolderKanban /></span></Card>
      <Card className="metric"><span className="metric-label">My projects</span><strong className="metric-value">{data.projects.length}</strong><span className="metric-icon"><FolderKanban /></span></Card>
      <Card className="metric"><span className="metric-label">My teams</span><strong className="metric-value">{data.teams.length}</strong><span className="metric-icon"><Users /></span></Card>
    </div>
    <div className="content-grid">
      <Card><CardHeader title="My tasks" description="Open work assigned to you" />{data.tasks.length ? <div className="stack">{data.tasks.map((task) => <Link className="split" href={`/projects/${task.project_id}/kanban`} key={task.id}><div><strong className="mono small">{task.reference}</strong><div>{task.title}</div></div><Badge className={`priority-${task.priority}`}>{task.priority}</Badge></Link>)}</div> : <EmptyState title="No open tasks" description="Assigned tasks will appear here." />}</Card>
      <Card><CardHeader title="Upcoming meetings" description="Meetings you are attending" />{data.upcoming_meetings.length ? <div className="stack">{data.upcoming_meetings.map((meeting) => <div className="split" key={meeting.id}><div><strong>{meeting.title}</strong><div className="muted small">{formatDate(meeting.start, true)}</div></div><Badge>{meeting.scope_type}</Badge></div>)}</div> : <EmptyState title="No upcoming meetings" description="New invitations will appear automatically." />}</Card>
      <Card><CardHeader title="Projects" description="Your active workspaces" />{data.projects.length ? <div className="stack">{data.projects.map((project) => <Link className="split" href={`/projects/${project.id}`} key={project.id}><div><strong>{project.name}</strong><div className="muted mono small">{project.key}</div></div><Badge className="badge-success">{project.status}</Badge></Link>)}</div> : <EmptyState title="No projects" description="Projects become visible through team membership." />}</Card>
      <Card><CardHeader title="Upcoming events" description="Next 30 days" action={<CalendarDays />} />{data.upcoming_events.length ? <div className="stack">{data.upcoming_events.map((event) => <div className="split" key={event.id}><div><strong>{event.title}</strong><div className="muted small">{formatDate(event.start, true)}</div></div><Badge>{event.scope_type}</Badge></div>)}</div> : <EmptyState title="Calendar is clear" description="Create an event or accept a meeting invitation." />}</Card>
    </div>
  </>;
}

