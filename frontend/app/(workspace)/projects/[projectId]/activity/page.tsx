"use client";

import { History } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { UserIdentity } from "@/components/user-avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
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

function ActivityValues({
  changes,
  side,
}: {
  changes: TaskActivity["changes"];
  side: "before" | "after";
}) {
  const entries = Object.entries(changes);
  if (!entries.length) return <span>—</span>;
  return <div className="activity-values-list">{entries.map(([field, change]) => <div className="activity-value-item" key={field}><span className="muted small">{fieldLabels[field] ?? field.replaceAll("_", " ")}</span><span>{displayValue(change[side])}</span></div>)}</div>;
}

export default function ProjectActivityPage() {
  const { project } = useProject(); const [page, setPage] = useState(1); const resource = useResource<Paginated<TaskActivity>>(`/projects/${project.id}/activity?page=${page}&page_size=50`);
  if (resource.loading) return <LoadingState label="Loading project activity…" />;
  if (resource.error || !resource.data) return <ErrorState message={resource.error ?? "Activity log unavailable"} retry={resource.reload} />;
  return <><div className="page-header"><div><h2>Ticket activity</h2><p>Permanent history of ticket creation, edits, moves and comments.</p></div><History /></div>{resource.data.items.length ? <div className="table-wrap"><table className="activity-table"><thead><tr><th>User</th><th>Before</th><th>After</th></tr></thead><tbody>{resource.data.items.map((entry) => <tr key={entry.id}><td><div className="activity-user-cell">{entry.actor ? <UserIdentity user={entry.actor} compact linked /> : <strong>Deleted user</strong>}<span className="muted small">{formatDate(entry.created_at, true)}</span><Link className="activity-ticket-cell" href={`/projects/${project.id}/kanban`}><span><span className="mono small">{entry.task_reference}</span> <Badge>{entry.action}</Badge></span><span className="muted small">{entry.task_title}</span></Link></div></td><td className="activity-value-cell"><ActivityValues changes={entry.changes} side="before" /></td><td className="activity-value-cell"><ActivityValues changes={entry.changes} side="after" /></td></tr>)}</tbody></table></div> : <EmptyState title="No ticket activity yet" description="Ticket changes will appear here." />}{resource.data.meta.pages > 1 ? <div className="pagination"><Button variant="outline" disabled={page <= 1} onClick={() => setPage((current) => current - 1)}>Previous</Button><span className="muted small">Page {page} of {resource.data.meta.pages}</span><Button variant="outline" disabled={page >= resource.data.meta.pages} onClick={() => setPage((current) => current + 1)}>Next</Button></div> : null}</>;
}
