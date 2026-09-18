"use client";

import { Clock, ListTree, MessageSquare, Pencil, Plus } from "lucide-react";
import { FormEvent, useState } from "react";

import { Button } from "@/components/ui/button";
import { UserAvatar, UserIdentity } from "@/components/user-avatar";
import { ConfirmDialog, Dialog } from "@/components/ui/dialog";
import { Field, Input, Select, Textarea } from "@/components/ui/form";
import { SearchableSelect } from "@/components/ui/searchable-select";
import { ErrorState, LoadingState } from "@/components/ui/states";
import { useToast } from "@/components/ui/toast";
import { useAuth } from "@/features/auth/auth-context";
import { useProject } from "@/features/projects/project-context";
import { useResource } from "@/hooks/use-resource";
import { formatDate, formatDuration } from "@/lib/utils";
import { api, jsonBody } from "@/services/api";
import type { Board, Sprint, Task, TaskComment, UserBrief } from "@/types/api";

type TimeParts = { hours: string; minutes: string; seconds: string };

const emptyTime: TimeParts = { hours: "", minutes: "", seconds: "" };

function timeParts(totalSeconds: number): TimeParts {
  return {
    hours: String(Math.floor(totalSeconds / 3600)),
    minutes: String(Math.floor((totalSeconds % 3600) / 60)),
    seconds: String(totalSeconds % 60),
  };
}

function timeInSeconds(value: TimeParts): number {
  return (
    Number(value.hours || 0) * 3600 + Number(value.minutes || 0) * 60 + Number(value.seconds || 0)
  );
}

function TimeInput({
  value,
  onChange,
}: {
  value: TimeParts;
  onChange: (value: TimeParts) => void;
}) {
  return (
    <fieldset className="time-input">
      <legend className="sr-only">Time tracking</legend>
      <div className="time-tracking-heading">
        <span className="time-tracking-icon">
          <Clock aria-hidden />
        </span>
        <strong>Time tracking</strong>
        <span className="time-tracking-total">{formatDuration(timeInSeconds(value))}</span>
      </div>
      <div className="time-input-grid">
        {(["hours", "minutes", "seconds"] as const).map((part) => (
          <label key={part}>
            <span>{part[0].toUpperCase() + part.slice(1)}</span>
            <Input
              type="number"
              min={0}
              max={part === "hours" ? 87600 : 59}
              step={1}
              value={value[part]}
              placeholder="00"
              onChange={(event) => onChange({ ...value, [part]: event.target.value })}
            />
          </label>
        ))}
      </div>
    </fieldset>
  );
}

export function KanbanBoard() {
  const { project } = useProject();
  const { hasPermission } = useAuth();
  const resource = useResource<Board>(`/projects/${project.id}/board`);
  const members = useResource<UserBrief[]>(`/projects/${project.id}/members`);
  const sprints = useResource<Sprint[]>(
    hasPermission("scrum.view") ? `/projects/${project.id}/sprints` : null,
  );
  const { notify } = useToast();
  const [open, setOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [dragged, setDragged] = useState<string>();
  const [form, setForm] = useState({
    title: "",
    description: "",
    type: "task",
    priority: "medium",
    assignee_id: "",
    sprint_id: "",
    ...emptyTime,
  });
  const [selected, setSelected] = useState<Task>();
  const [editing, setEditing] = useState<Task>();
  async function create(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    try {
      const { hours, minutes, seconds, ...values } = form;
      await api(`/projects/${project.id}/tasks`, {
        method: "POST",
        body: jsonBody({
          ...values,
          assignee_id: form.assignee_id || null,
          sprint_id: form.sprint_id || null,
          tracked_seconds: timeInSeconds({ hours, minutes, seconds }),
        }),
      });
      setOpen(false);
      setForm({
        title: "",
        description: "",
        type: "task",
        priority: "medium",
        assignee_id: "",
        sprint_id: "",
        ...emptyTime,
      });
      notify("Task created");
      await resource.reload();
    } catch (reason) {
      notify((reason as Error).message, "error");
    } finally {
      setSaving(false);
    }
  }
  async function drop(columnId: string, beforeTaskId?: string) {
    if (!dragged || dragged === beforeTaskId) return;
    const previous = resource.data;
    if (previous)
      resource.setData({
        ...previous,
        tasks: previous.tasks.map((task) =>
          task.id === dragged ? { ...task, kanban_column_id: columnId } : task,
        ),
      });
    try {
      await api(`/projects/${project.id}/board/tasks/${dragged}/move`, {
        method: "POST",
        body: jsonBody({ column_id: columnId, before_task_id: beforeTaskId ?? null }),
      });
      await resource.reload();
    } catch (reason) {
      resource.setData(previous);
      notify((reason as Error).message, "error");
    } finally {
      setDragged(undefined);
    }
  }
  if (resource.loading) return <LoadingState label="Loading board…" />;
  if (resource.error || !resource.data)
    return <ErrorState message={resource.error ?? "Board unavailable"} retry={resource.reload} />;
  return (
    <>
      <div className="page-header">
        <div>
          <h2>Kanban board</h2>
          <p>Drag tasks between columns. Order and status are persisted.</p>
        </div>
        {hasPermission("kanban.manage") ? (
          <Button onClick={() => setOpen(true)}>
            <Plus />
            Create task
          </Button>
        ) : null}
      </div>
      <div className="kanban-board">
        {resource.data.columns.map((column) => {
          const tasks = resource.data!.tasks.filter((task) => task.kanban_column_id === column.id);
          return (
            <section
              className="kanban-column"
              key={column.id}
              onDragOver={(event) => event.preventDefault()}
              onDrop={() => drop(column.id)}
            >
              <div className="kanban-column-header">
                <span>{column.name}</span>
                <span className="badge">{tasks.length}</span>
              </div>
              <div className="kanban-cards">
                {tasks.map((task) => (
                  <TaskCard
                    task={task}
                    key={task.id}
                    draggable={hasPermission("kanban.manage")}
                    onDrag={() => setDragged(task.id)}
                    onDropBefore={(event) => {
                      event.stopPropagation();
                      void drop(column.id, task.id);
                    }}
                    onSelect={() => setSelected(task)}
                  />
                ))}
              </div>
            </section>
          );
        })}
      </div>
      <Dialog open={open} onOpenChange={setOpen} title="Create task">
        <form className="form-grid" onSubmit={create}>
          <Field label="Title">
            <Input
              required
              autoFocus
              value={form.title}
              onChange={(event) => setForm({ ...form, title: event.target.value })}
            />
          </Field>
          <Field label="Description">
            <Textarea
              value={form.description}
              onChange={(event) => setForm({ ...form, description: event.target.value })}
            />
          </Field>
          <div className="form-grid two">
            <Field label="Type">
              <Select
                value={form.type}
                onChange={(event) => setForm({ ...form, type: event.target.value })}
              >
                <option value="task">Task</option>
                <option value="story">Story</option>
                <option value="bug">Bug</option>
                <option value="epic">Epic</option>
              </Select>
            </Field>
            <Field label="Priority">
              <Select
                value={form.priority}
                onChange={(event) => setForm({ ...form, priority: event.target.value })}
              >
                <option value="lowest">Lowest</option>
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
                <option value="highest">Highest</option>
              </Select>
            </Field>
            <Field label="Assignee">
              <SearchableSelect
                options={[
                  { value: "", label: "Unassigned" },
                  ...(members.data?.map((member) => ({
                    value: member.id,
                    label: member.display_name,
                    description: `@${member.username}`,
                  })) ?? []),
                ]}
                value={form.assignee_id}
                onValueChange={(assignee_id) => setForm({ ...form, assignee_id })}
                searchPlaceholder="Search project members…"
              />
            </Field>
            <Field label="Sprint">
              <SearchableSelect
                options={[
                  { value: "", label: "Backlog" },
                  ...(sprints.data
                    ?.filter((sprint) => sprint.status === "planned" || sprint.status === "active")
                    .map((sprint) => ({
                      value: sprint.id,
                      label: sprint.name,
                      description: sprint.status,
                    })) ?? []),
                ]}
                value={form.sprint_id}
                onValueChange={(sprint_id) => setForm({ ...form, sprint_id })}
                searchPlaceholder="Search sprints…"
              />
            </Field>
          </div>
          <TimeInput
            value={form}
            onChange={(trackedTime) => setForm({ ...form, ...trackedTime })}
          />
          <div className="dialog-actions">
            <Button type="button" variant="outline" onClick={() => setOpen(false)}>
              Cancel
            </Button>
            <Button loading={saving}>Create task</Button>
          </div>
        </form>
      </Dialog>
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

function TaskCard({
  task,
  draggable,
  onDrag,
  onDropBefore,
  onSelect,
}: {
  task: Task;
  draggable: boolean;
  onDrag: () => void;
  onDropBefore: (event: React.DragEvent) => void;
  onSelect: () => void;
}) {
  return (
    <article
      className="task-card"
      draggable={draggable}
      onDragStart={onDrag}
      onDragOver={(event) => event.preventDefault()}
      onDrop={onDropBefore}
      onClick={onSelect}
      tabIndex={0}
      onKeyDown={(event) => event.key === "Enter" && onSelect()}
    >
      <div className="split">
        <span className="mono small muted">{task.reference}</span>
        <span className={`badge priority-${task.priority}`}>{task.priority}</span>
      </div>
      <div className="task-card-title">{task.title}</div>
      <div className="task-card-meta">
        <span>
          {task.parent_task_id ? "subticket" : task.type}
          {task.tracked_seconds ? ` · ${formatDuration(task.tracked_seconds)}` : ""}
        </span>
        <span>
          {task.assignee ? (
            <span className="user-identity">
              <UserAvatar user={task.assignee} size={22} />
              <span>{task.assignee.first_name}</span>
            </span>
          ) : (
            "Unassigned"
          )}
        </span>
      </div>
    </article>
  );
}

function TaskDetailDialog({
  task,
  projectId,
  sprints,
  canEdit,
  onChanged,
  onSelectTask,
  onClose,
  onEdit,
}: {
  task: Task;
  projectId: string;
  sprints: Sprint[];
  canEdit: boolean;
  onChanged: () => Promise<void>;
  onSelectTask: (task: Task) => void;
  onClose: () => void;
  onEdit: () => void;
}) {
  const comments = useResource<TaskComment[]>(`/projects/${projectId}/tasks/${task.id}/comments`);
  const subtasks = useResource<Task[]>(`/projects/${projectId}/tasks/${task.id}/subtasks`);
  const { notify } = useToast();
  const [body, setBody] = useState("");
  const [subtaskTitle, setSubtaskTitle] = useState("");
  const [saving, setSaving] = useState(false);
  const [savingSubtask, setSavingSubtask] = useState(false);
  const sprint = sprints.find((item) => item.id === task.sprint_id);
  async function comment(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    try {
      await api(`/projects/${projectId}/tasks/${task.id}/comments`, {
        method: "POST",
        body: jsonBody({ body }),
      });
      setBody("");
      await comments.reload();
    } catch (reason) {
      notify((reason as Error).message, "error");
    } finally {
      setSaving(false);
    }
  }
  async function createSubtask(event: FormEvent) {
    event.preventDefault();
    setSavingSubtask(true);
    try {
      await api<Task>(`/projects/${projectId}/tasks/${task.id}/subtasks`, {
        method: "POST",
        body: jsonBody({
          title: subtaskTitle,
          priority: task.priority,
          assignee_id: task.assignee?.id ?? null,
          sprint_id: task.sprint_id,
        }),
      });
      setSubtaskTitle("");
      notify("Subticket created");
      await Promise.all([subtasks.reload(), onChanged()]);
    } catch (reason) {
      notify((reason as Error).message, "error");
    } finally {
      setSavingSubtask(false);
    }
  }
  return (
    <Dialog
      open
      onOpenChange={(value) => !value && onClose()}
      title={task.reference}
      description={task.title}
    >
      <div className="task-detail">
        <div className="inline-list">
          <span className="badge">{task.status.replaceAll("_", " ")}</span>
          <span className="badge">{task.type}</span>
          {task.parent_task_id ? <span className="badge">subticket</span> : null}
          <span className={`badge priority-${task.priority}`}>{task.priority}</span>
        </div>
        <div className="task-detail-grid">
          <div>
            <span className="muted small">Reporter</span>
            <div className="task-detail-value">
              <UserIdentity user={task.reporter} compact linked />
            </div>
          </div>
          <div>
            <span className="muted small">Assignee</span>
            <div className="task-detail-value">
              {task.assignee ? <UserIdentity user={task.assignee} compact linked /> : "Unassigned"}
            </div>
          </div>
          <div>
            <span className="muted small">Sprint</span>
            <div className="task-detail-value">
              {sprint?.name ?? (task.sprint_id ? "Assigned sprint" : "Backlog")}
            </div>
          </div>
          <div>
            <span className="muted small">Due date</span>
            <div className="task-detail-value">{formatDate(task.due_date, true)}</div>
          </div>
          {task.completed_at ? (
            <div>
              <span className="muted small">Completed</span>
              <div className="task-detail-value">{formatDate(task.completed_at, true)}</div>
            </div>
          ) : null}
        </div>
        <section className="time-tracking-summary" aria-label="Time tracking">
          <div className="time-tracking-heading">
            <span className="time-tracking-icon">
              <Clock aria-hidden />
            </span>
            <strong>Tracked time</strong>
          </div>
          <strong className="time-tracking-total">{formatDuration(task.tracked_seconds)}</strong>
        </section>
        <div>
          <span className="muted small">Description</span>
          <div className="task-description">{task.description || "No description provided."}</div>
        </div>
        <section className="task-subtasks">
          <div className="split">
            <h3>
              <ListTree /> Subtickets
            </h3>
            <span className="badge">{subtasks.data?.length ?? 0}</span>
          </div>
          {subtasks.loading ? (
            <p className="muted small">Loading subtickets…</p>
          ) : subtasks.error ? (
            <p className="field-error">{subtasks.error}</p>
          ) : subtasks.data?.length ? (
            <div className="subtask-list">
              {subtasks.data.map((subtask) => (
                <button
                  type="button"
                  className="subtask-row"
                  key={subtask.id}
                  onClick={() => onSelectTask(subtask)}
                >
                  <span>
                    <span className="mono small muted">{subtask.reference}</span>
                    <strong>{subtask.title}</strong>
                  </span>
                  <span className="badge">{subtask.status.replaceAll("_", " ")}</span>
                </button>
              ))}
            </div>
          ) : (
            <p className="muted small">No subtickets yet.</p>
          )}
          {canEdit ? (
            <form className="subtask-create" onSubmit={createSubtask}>
              <Input
                required
                maxLength={300}
                value={subtaskTitle}
                onChange={(event) => setSubtaskTitle(event.target.value)}
                placeholder="New subticket title"
                aria-label="New subticket title"
              />
              <Button loading={savingSubtask} disabled={!subtaskTitle.trim()}>
                <Plus />
                Add
              </Button>
            </form>
          ) : null}
        </section>
        <section className="task-comments">
          <h3>Comments</h3>
          {comments.loading ? (
            <p className="muted small">Loading comments…</p>
          ) : comments.error ? (
            <p className="field-error">{comments.error}</p>
          ) : comments.data?.length ? (
            comments.data.map((comment) => (
              <article className="task-comment" key={comment.id}>
                <div className="task-comment-header">
                  <UserIdentity user={comment.author} compact linked />
                  <span className="muted small">{formatDate(comment.created_at, true)}</span>
                </div>
                <p>{comment.body}</p>
              </article>
            ))
          ) : (
            <p className="muted small">No comments yet.</p>
          )}
          <form className="form-grid" onSubmit={comment}>
            <Field label="Add comment">
              <Textarea
                required
                maxLength={10000}
                value={body}
                onChange={(event) => setBody(event.target.value)}
                placeholder="Write a comment…"
              />
            </Field>
            <div className="form-actions">
              <Button loading={saving} disabled={!body.trim()}>
                <MessageSquare />
                Comment
              </Button>
            </div>
          </form>
        </section>
        <div className="dialog-actions">
          <Button variant="outline" onClick={onClose}>
            Close
          </Button>
          {canEdit ? (
            <Button onClick={onEdit}>
              <Pencil />
              Edit task
            </Button>
          ) : null}
        </div>
      </div>
    </Dialog>
  );
}

function TaskEditDialog({
  task,
  projectId,
  members,
  sprints,
  onClose,
  onSaved,
}: {
  task: Task;
  projectId: string;
  members: UserBrief[];
  sprints: Sprint[];
  onClose: () => void;
  onSaved: () => Promise<void>;
}) {
  const { notify } = useToast();
  const [saving, setSaving] = useState(false);
  const [confirm, setConfirm] = useState(false);
  const [form, setForm] = useState({
    title: task.title,
    description: task.description ?? "",
    type: task.type,
    priority: task.priority,
    assignee_id: task.assignee?.id ?? "",
    sprint_id: task.sprint_id ?? "",
    due_date: task.due_date?.slice(0, 16) ?? "",
    ...timeParts(task.tracked_seconds),
  });
  async function save(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    try {
      const { hours, minutes, seconds, ...values } = form;
      await api(`/projects/${projectId}/tasks/${task.id}`, {
        method: "PATCH",
        body: jsonBody({
          ...values,
          assignee_id: form.assignee_id || null,
          sprint_id: form.sprint_id || null,
          due_date: form.due_date ? new Date(form.due_date).toISOString() : null,
          tracked_seconds: timeInSeconds({ hours, minutes, seconds }),
        }),
      });
      notify("Task updated");
      await onSaved();
      onClose();
    } catch (reason) {
      notify((reason as Error).message, "error");
    } finally {
      setSaving(false);
    }
  }
  async function remove() {
    setSaving(true);
    try {
      await api(`/projects/${projectId}/tasks/${task.id}`, { method: "DELETE" });
      notify("Task deleted");
      await onSaved();
      onClose();
    } catch (reason) {
      notify((reason as Error).message, "error");
      setSaving(false);
    }
  }
  return (
    <>
      <Dialog open onOpenChange={(value) => !value && onClose()} title={`Edit ${task.reference}`}>
        <form className="form-grid" onSubmit={save}>
          <div>
            <span className="muted small">Reporter</span>
            <div style={{ marginTop: "0.35rem" }}>
              <UserIdentity user={task.reporter} compact linked />
            </div>
          </div>
          <Field label="Title">
            <Input
              required
              autoFocus
              value={form.title}
              onChange={(event) => setForm({ ...form, title: event.target.value })}
            />
          </Field>
          <Field label="Description">
            <Textarea
              value={form.description}
              onChange={(event) => setForm({ ...form, description: event.target.value })}
            />
          </Field>
          <div className="form-grid two">
            <Field label="Type">
              <Select
                value={form.type}
                onChange={(event) => setForm({ ...form, type: event.target.value as Task["type"] })}
              >
                <option value="task">Task</option>
                <option value="story">Story</option>
                <option value="bug">Bug</option>
                <option value="epic">Epic</option>
              </Select>
            </Field>
            <Field label="Priority">
              <Select
                value={form.priority}
                onChange={(event) =>
                  setForm({ ...form, priority: event.target.value as Task["priority"] })
                }
              >
                <option value="lowest">Lowest</option>
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
                <option value="highest">Highest</option>
              </Select>
            </Field>
            <Field label="Assignee">
              <SearchableSelect
                options={[
                  { value: "", label: "Unassigned" },
                  ...members.map((member) => ({
                    value: member.id,
                    label: member.display_name,
                    description: `@${member.username}`,
                  })),
                ]}
                value={form.assignee_id}
                onValueChange={(assignee_id) => setForm({ ...form, assignee_id })}
                searchPlaceholder="Search project members…"
              />
            </Field>
            <Field label="Sprint">
              <SearchableSelect
                options={[
                  { value: "", label: "Backlog" },
                  ...sprints
                    .filter((sprint) => ["planned", "active"].includes(sprint.status))
                    .map((sprint) => ({
                      value: sprint.id,
                      label: sprint.name,
                      description: sprint.status,
                    })),
                ]}
                value={form.sprint_id}
                onValueChange={(sprint_id) => setForm({ ...form, sprint_id })}
                searchPlaceholder="Search sprints…"
              />
            </Field>
          </div>
          <Field label="Due date">
            <Input
              type="datetime-local"
              value={form.due_date}
              onChange={(event) => setForm({ ...form, due_date: event.target.value })}
            />
          </Field>
          <TimeInput
            value={form}
            onChange={(trackedTime) => setForm({ ...form, ...trackedTime })}
          />
          <div className="dialog-actions">
            <Button type="button" variant="destructive" onClick={() => setConfirm(true)}>
              Delete
            </Button>
            <Button type="button" variant="outline" onClick={onClose}>
              Cancel
            </Button>
            <Button loading={saving}>Save task</Button>
          </div>
        </form>
      </Dialog>
      <ConfirmDialog
        open={confirm}
        onOpenChange={setConfirm}
        title={`Delete ${task.reference}?`}
        description="This task will be permanently removed."
        onConfirm={remove}
        loading={saving}
      />
    </>
  );
}
