"use client";

import { ArrowRight, History } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { UserIdentity } from "@/components/user-avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/states";
import { useProject } from "@/features/projects/project-context";
import { useResource } from "@/hooks/use-resource";
import { formatDate } from "@/lib/utils";
import type { ActivityValue, Paginated, TaskActivity } from "@/types/api";

const fieldLabels: Record<string, string> = {
  assignee_id: "Assignee",
  column: "Column",
  comment: "Comment",
  description: "Description",
  due_date: "Due date",
  order: "Order",
  priority: "Priority",
  sprint_id: "Sprint",
  status: "Status",
  title: "Title",
  type: "Type",
};

function displayValue(value: ActivityValue): string {
  if (value === null || value === "") return "—";
  if (typeof value === "boolean") return value ? "Yes" : "No";
  return String(value);
}

export default function ProjectActivityPage() {
  const { project } = useProject(); const [page, setPage] = useState(1); const resource = useResource<Paginated<TaskActivity>>(`/projects/${project.id}/activity?page=${page}&page_size=50`);
  if (resource.loading) return <LoadingState label="Loading project activity…" />;
  if (resource.error || !resource.data) return <ErrorState message={resource.error ?? "Activity log unavailable"} retry={resource.reload} />;
  return <><div className="page-header"><div><h2>Ticket activity</h2><p>Permanent history of ticket creation, edits, moves and comments.</p></div><History /></div>{resource.data.items.length ? <div className="activity-list">{resource.data.items.map((entry) => <Card className="activity-entry" key={entry.id}><div className="activity-heading"><div>{entry.actor ? <UserIdentity user={entry.actor} compact linked /> : <strong>Deleted user</strong>}<span className="muted small">{formatDate(entry.created_at, true)}</span></div><Badge>{entry.action}</Badge></div><div><Link href={`/projects/${project.id}/kanban`}><span className="mono small muted">{entry.task_reference}</span><strong className="activity-task-title">{entry.task_title}</strong></Link></div>{Object.keys(entry.changes).length ? <div className="activity-changes">{Object.entries(entry.changes).map(([field, change]) => <div className="activity-change" key={field}><span className="muted small">{fieldLabels[field] ?? field.replaceAll("_", " ")}</span><div className="activity-values"><span>{displayValue(change.before)}</span><ArrowRight /><span>{displayValue(change.after)}</span></div></div>)}</div> : null}</Card>)}</div> : <EmptyState title="No ticket activity yet" description="Ticket changes will appear here." />}{resource.data.meta.pages > 1 ? <div className="pagination"><Button variant="outline" disabled={page <= 1} onClick={() => setPage((current) => current - 1)}>Previous</Button><span className="muted small">Page {page} of {resource.data.meta.pages}</span><Button variant="outline" disabled={page >= resource.data.meta.pages} onClick={() => setPage((current) => current + 1)}>Next</Button></div> : null}</>;
}
