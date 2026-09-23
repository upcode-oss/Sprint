"use client";

import { useState } from "react";

import { UserIdentity } from "@/components/user-avatar";
import { Button } from "@/components/ui/button";
import { Input, Select } from "@/components/ui/form";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/states";
import { useAuth } from "@/features/auth/auth-context";
import { TaskDetailDialog, TaskEditDialog } from "@/features/kanban/kanban-board";
import { useProject } from "@/features/projects/project-context";
import { useResource } from "@/hooks/use-resource";
import { formatDate, formatDuration } from "@/lib/utils";
import type { Sprint, Task, UserBrief } from "@/types/api";

export default function ProjectTicketsPage() {
  const { project } = useProject();
  const { hasPermission } = useAuth();
  // The task endpoint includes completed tickets hidden by the board retention setting.
  const resource = useResource<Task[]>(`/projects/${project.id}/tasks`);
  const members = useResource<UserBrief[]>(
    hasPermission("kanban.manage") ? `/projects/${project.id}/members` : null,
  );
  const sprints = useResource<Sprint[]>(
    hasPermission("scrum.view") ? `/projects/${project.id}/sprints` : null,
  );
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");
  const [selected, setSelected] = useState<Task>();
  const [editing, setEditing] = useState<Task>();

  if (resource.loading) return <LoadingState label="Loading tickets…" />;
  if (resource.error || !resource.data)
    return <ErrorState message={resource.error ?? "Tickets unavailable"} retry={resource.reload} />;

  const query = search.trim().toLowerCase();
  const tasks = resource.data
    .filter(
      (task) =>
        (!status || task.status === status) &&
        `${task.reference} ${task.title} ${task.description ?? ""}`.toLowerCase().includes(query),
    )
    .sort((a, b) => b.number - a.number);
  const statuses = [...new Set(resource.data.map((task) => task.status))].sort();

  return (
    <>
      <div className="page-header">
        <div>
          <h2>All tickets</h2>
          <p>All project tickets, including subtickets and completed tickets hidden from Kanban.</p>
        </div>
      </div>
      <div className="toolbar">
        <Input
          aria-label="Search tickets"
          placeholder="Search by reference, title or description…"
          value={search}
          onChange={(event) => setSearch(event.target.value)}
        />
        <Select
          aria-label="Filter by status"
          value={status}
          onChange={(event) => setStatus(event.target.value)}
        >
          <option value="">All statuses</option>
          {statuses.map((value) => (
            <option key={value} value={value}>
              {value.replaceAll("_", " ")}
            </option>
          ))}
        </Select>
        <span className="muted small" role="status">
          {tasks.length} of {resource.data.length} tickets
        </span>
      </div>
      {tasks.length ? (
        <div className="table-wrap">
          <table aria-label="All project tickets">
            <thead>
              <tr>
                <th>Ticket</th>
                <th>Title</th>
                <th>Status</th>
                <th>Type</th>
                <th>Priority</th>
                <th>Assignee</th>
                <th>Due date</th>
                <th>Completed</th>
                <th>Tracked time</th>
              </tr>
            </thead>
            <tbody>
              {tasks.map((task) => (
                <tr key={task.id}>
                  <td>
                    <Button variant="ghost" size="sm" onClick={() => setSelected(task)}>
                      {task.reference}
                    </Button>
                  </td>
                  <td>{task.title}</td>
                  <td>
                    <span className="badge">{task.status.replaceAll("_", " ")}</span>
                  </td>
                  <td>{task.parent_task_id ? "subticket" : task.type}</td>
                  <td>
                    <span className={`badge priority-${task.priority}`}>{task.priority}</span>
                  </td>
                  <td>
                    {task.assignee ? (
                      <UserIdentity user={task.assignee} compact linked />
                    ) : (
                      "Unassigned"
                    )}
                  </td>
                  <td>{formatDate(task.due_date)}</td>
                  <td>{formatDate(task.completed_at)}</td>
                  <td>{formatDuration(task.tracked_seconds)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <EmptyState
          title={resource.data.length ? "No matching tickets" : "No tickets yet"}
          description={
            resource.data.length
              ? "Try another search or status filter."
              : "Create your first ticket on the Kanban board."
          }
        />
      )}
      {selected ? (
        <TaskDetailDialog
          key={selected.id}
          task={selected}
          projectId={project.id}
          sprints={sprints.data ?? []}
          canEdit={hasPermission("kanban.manage")}
          onChanged={resource.reload}
          onSelectTask={setSelected}
          onClose={() => setSelected(undefined)}
          onEdit={() => {
            setEditing(selected);
            setSelected(undefined);
          }}
        />
      ) : null}
      {editing ? (
        <TaskEditDialog
          key={editing.id}
          task={editing}
          projectId={project.id}
          members={members.data ?? []}
          sprints={sprints.data ?? []}
          onClose={() => setEditing(undefined)}
          onSaved={resource.reload}
        />
      ) : null}
    </>
  );
}
