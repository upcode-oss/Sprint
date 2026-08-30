"use client";

import { CalendarDays, Clock, FileText, ListChecks, Users } from "lucide-react";
import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { Card, CardHeader } from "@/components/ui/card";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/states";
import { useProject } from "@/features/projects/project-context";
import { useResource } from "@/hooks/use-resource";
import { formatDate, formatDuration } from "@/lib/utils";
import type { ProjectOverview } from "@/types/api";

export default function ProjectOverviewPage() {
  const { project } = useProject(); const { data, error, loading, reload } = useResource<ProjectOverview>(`/projects/${project.id}/overview`);
  if (loading) return <LoadingState />; if (error || !data) return <ErrorState message={error ?? "Overview unavailable"} retry={reload} />;
  return <><div className="metrics-grid"><Card className="metric"><span className="metric-label">Current tasks</span><strong className="metric-value">{data.tasks.length}</strong><span className="metric-icon"><ListChecks /></span></Card><Card className="metric"><span className="metric-label">Tracked time</span><strong className="metric-value">{formatDuration(data.total_tracked_minutes)}</strong><span className="metric-icon"><Clock /></span></Card><Card className="metric"><span className="metric-label">Active sprint</span><strong className="metric-value" style={{ fontSize: "1.15rem" }}>{data.active_sprint?.name ?? "None"}</strong><span className="metric-icon"><ListChecks /></span></Card><Card className="metric"><span className="metric-label">Members</span><strong className="metric-value">{data.member_count}</strong><span className="metric-icon"><Users /></span></Card><Card className="metric"><span className="metric-label">Upcoming meetings</span><strong className="metric-value">{data.upcoming_meetings.length}</strong><span className="metric-icon"><CalendarDays /></span></Card></div><div className="content-grid"><Card><CardHeader title="Current tasks" />{data.tasks.length ? <div className="stack">{data.tasks.map((task) => <Link href={`/projects/${project.id}/kanban`} className="split" key={task.id}><div><span className="mono small muted">{task.reference}</span><div>{task.title}</div></div><Badge>{task.status.replaceAll("_", " ")}</Badge></Link>)}</div> : <EmptyState title="No tasks" description="Create the first task on the Kanban board." />}</Card><Card><CardHeader title="Upcoming meetings" />{data.upcoming_meetings.length ? <div className="stack">{data.upcoming_meetings.map((meeting) => <div key={meeting.id}><strong>{meeting.title}</strong><div className="muted small">{formatDate(meeting.start, true)}</div></div>)}</div> : <EmptyState title="No meetings" description="Schedule a project meeting when needed." />}</Card><Card className="wide"><CardHeader title="Recent document changes" action={<FileText />} />{data.recent_documents.length ? <div className="stack">{data.recent_documents.map((document) => <Link href={`/projects/${project.id}/documents`} className="split" key={document.id}><strong>{document.title}</strong><span className="muted small">{formatDate(document.updated_at, true)}</span></Link>)}</div> : <EmptyState title="No documents" description="Project knowledge will appear here." />}</Card></div></>;
}
