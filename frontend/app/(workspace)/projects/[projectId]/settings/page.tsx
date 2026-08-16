"use client";

import { Save, Trash2 } from "lucide-react";
import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardHeader } from "@/components/ui/card";
import { ConfirmDialog } from "@/components/ui/dialog";
import { Field, Input, Select, Textarea } from "@/components/ui/form";
import { useToast } from "@/components/ui/toast";
import { useAuth } from "@/features/auth/auth-context";
import { useProject } from "@/features/projects/project-context";
import { useResource } from "@/hooks/use-resource";
import { api, jsonBody } from "@/services/api";
import type { Paginated, Team } from "@/types/api";

export default function ProjectSettingsPage() {
  const { project, reload } = useProject(); const { hasPermission } = useAuth(); const teams = useResource<Paginated<Team>>(hasPermission("projects.manage_members") ? "/teams?page_size=100" : null); const { notify } = useToast(); const router = useRouter(); const [saving, setSaving] = useState(false); const [confirm, setConfirm] = useState(false); const [form, setForm] = useState({ name: project.name, description: project.description ?? "", status: project.status, start_date: project.start_date ?? "", end_date: project.end_date ?? "", team_ids: project.teams.map((team) => team.id) });
  useEffect(() => setForm({ name: project.name, description: project.description ?? "", status: project.status, start_date: project.start_date ?? "", end_date: project.end_date ?? "", team_ids: project.teams.map((team) => team.id) }), [project]);
  async function save(event: FormEvent) { event.preventDefault(); setSaving(true); try { if (hasPermission("projects.edit")) await api(`/projects/${project.id}`, { method: "PATCH", body: jsonBody({ name: form.name, description: form.description, status: form.status, start_date: form.start_date || null, end_date: form.end_date || null }) }); if (hasPermission("projects.manage_members")) await api(`/projects/${project.id}/teams`, { method: "PUT", body: jsonBody({ ids: form.team_ids }) }); notify("Project settings saved"); await reload(); } catch (reason) { notify((reason as Error).message, "error"); } finally { setSaving(false); } }
  async function remove() { setSaving(true); try { await api(`/projects/${project.id}`, { method: "DELETE" }); notify("Project deleted"); router.replace("/projects"); } catch (reason) { notify((reason as Error).message, "error"); setSaving(false); } }
  return <div className="content-grid"><Card><CardHeader title="Project details" description="Update the lifecycle and planning dates." /><form className="form-grid" onSubmit={save}><Field label="Name"><Input disabled={!hasPermission("projects.edit")} required value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} /></Field><Field label="Key" hint="Project keys remain stable because they identify every task."><Input disabled value={project.key} className="mono" /></Field><Field label="Description"><Textarea disabled={!hasPermission("projects.edit")} value={form.description} onChange={(event) => setForm({ ...form, description: event.target.value })} /></Field><Field label="Status"><Select disabled={!hasPermission("projects.edit")} value={form.status} onChange={(event) => setForm({ ...form, status: event.target.value })}><option value="planned">Planned</option><option value="active">Active</option><option value="on_hold">On hold</option><option value="completed">Completed</option><option value="archived">Archived</option></Select></Field><div className="form-grid two"><Field label="Start date"><Input type="date" value={form.start_date} onChange={(event) => setForm({ ...form, start_date: event.target.value })} /></Field><Field label="End date"><Input type="date" value={form.end_date} onChange={(event) => setForm({ ...form, end_date: event.target.value })} /></Field></div>{hasPermission("projects.manage_members") ? <Field label="Teams" hint="Project access is derived from these teams."><Select multiple value={form.team_ids} onChange={(event) => setForm({ ...form, team_ids: Array.from(event.target.selectedOptions, (option) => option.value) })}>{teams.data?.items.map((team) => <option value={team.id} key={team.id}>{team.name}</option>)}</Select></Field> : null}<div className="form-actions"><Button loading={saving}><Save />Save settings</Button></div></form></Card>{hasPermission("projects.delete") ? <Card><CardHeader title="Danger zone" description="Deleting a project removes its tasks, sprints, board and documents." /><Button variant="destructive" onClick={() => setConfirm(true)}><Trash2 />Delete project</Button></Card> : null}<ConfirmDialog open={confirm} onOpenChange={setConfirm} title={`Delete ${project.name}?`} description="This operation cannot be undone and removes all project data." onConfirm={remove} loading={saving} /></div>;
}

