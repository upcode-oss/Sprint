"use client";

import { FolderKanban, Plus } from "lucide-react";
import Link from "next/link";
import { FormEvent, useState } from "react";

import { PageHeader } from "@/components/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Dialog } from "@/components/ui/dialog";
import { Field, Input, Select, Textarea } from "@/components/ui/form";
import { SearchableMultiSelect } from "@/components/ui/searchable-select";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/states";
import { useToast } from "@/components/ui/toast";
import { useAuth } from "@/features/auth/auth-context";
import { useResource } from "@/hooks/use-resource";
import { api, jsonBody } from "@/services/api";
import type { Paginated, Project, Team } from "@/types/api";

export function ProjectList() {
  const { hasPermission } = useAuth(); const { data, error, loading, reload } = useResource<Paginated<Project>>("/projects?page_size=100"); const teams = useResource<Paginated<Team>>(hasPermission("projects.create") ? "/teams?page_size=100" : null); const { notify } = useToast();
  const [open, setOpen] = useState(false); const [saving, setSaving] = useState(false); const [form, setForm] = useState({ name: "", key: "", description: "", status: "active", team_ids: [] as string[] });
  async function submit(event: FormEvent) { event.preventDefault(); setSaving(true); try { await api("/projects", { method: "POST", body: jsonBody(form) }); setOpen(false); setForm({ name: "", key: "", description: "", status: "active", team_ids: [] }); notify("Project created"); await reload(); } catch (reason) { notify((reason as Error).message, "error"); } finally { setSaving(false); } }
  return <>
    <PageHeader title="Projects" description="Project workspaces available through your teams." actions={hasPermission("projects.create") ? <Button onClick={() => setOpen(true)}><Plus />Create project</Button> : undefined} />
    {loading ? <LoadingState /> : error ? <ErrorState message={error} retry={reload} /> : data?.items.length ? <div className="content-grid">{data.items.map((project) => <Link href={`/projects/${project.id}`} key={project.id}><Card><div className="split"><span className="metric-icon" style={{ position: "static" }}><FolderKanban /></span><Badge className={project.status === "active" ? "badge-success" : ""}>{project.status}</Badge></div><h2 style={{ marginTop: "1rem" }}>{project.name}</h2><p className="mono small muted">{project.key}</p><p className="muted">{project.description || "No description provided."}</p><div className="inline-list">{project.teams.map((team) => <Badge key={team.id}>{team.name}</Badge>)}</div></Card></Link>)}</div> : <EmptyState title="No projects yet" description="Create a project and attach one or more teams." />}
    <Dialog open={open} onOpenChange={setOpen} title="Create project" description="A standard Kanban board is created automatically."><form className="form-grid" onSubmit={submit}><div className="form-grid two"><Field label="Name"><Input required autoFocus value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} /></Field><Field label="Key"><Input required minLength={2} maxLength={20} value={form.key} onChange={(event) => setForm({ ...form, key: event.target.value.toUpperCase().replace(/[^A-Z0-9]/g, "") })} /></Field></div><Field label="Description"><Textarea value={form.description} onChange={(event) => setForm({ ...form, description: event.target.value })} /></Field><Field label="Status"><Select value={form.status} onChange={(event) => setForm({ ...form, status: event.target.value })}><option value="planned">Planned</option><option value="active">Active</option><option value="on_hold">On hold</option></Select></Field><Field label="Teams"><SearchableMultiSelect options={teams.data?.items.map((team) => ({ value: team.id, label: team.name, description: team.description ?? undefined })) ?? []} values={form.team_ids} onValuesChange={(team_ids) => setForm({ ...form, team_ids })} placeholder="Select teams" searchPlaceholder="Search teams…" /></Field><div className="dialog-actions"><Button type="button" variant="outline" onClick={() => setOpen(false)}>Cancel</Button><Button loading={saving}>Create project</Button></div></form></Dialog>
  </>;
}
