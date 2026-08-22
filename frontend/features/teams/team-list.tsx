"use client";

import { Plus, Users } from "lucide-react";
import { FormEvent, useState } from "react";

import { PageHeader } from "@/components/page-header";
import { UserIdentity } from "@/components/user-avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Dialog } from "@/components/ui/dialog";
import { Field, Input, Textarea } from "@/components/ui/form";
import { SearchableMultiSelect } from "@/components/ui/searchable-select";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/states";
import { useToast } from "@/components/ui/toast";
import { useAuth } from "@/features/auth/auth-context";
import { useResource } from "@/hooks/use-resource";
import { api, jsonBody } from "@/services/api";
import type { Paginated, Team, User } from "@/types/api";

export function TeamList() {
  const { hasPermission } = useAuth(); const { data, error, loading, reload } = useResource<Paginated<Team>>("/teams?page_size=100"); const users = useResource<Paginated<User>>(hasPermission("teams.manage_members") ? "/users?page_size=100&active=true" : null); const { notify } = useToast();
  const [open, setOpen] = useState(false); const [saving, setSaving] = useState(false); const [editing, setEditing] = useState<Team>(); const [form, setForm] = useState({ name: "", description: "", member_ids: [] as string[] });
  function createDialog() { setEditing(undefined); setForm({ name: "", description: "", member_ids: [] }); setOpen(true); }
  function editDialog(team: Team) { setEditing(team); setForm({ name: team.name, description: team.description ?? "", member_ids: team.members.map((member) => member.id) }); setOpen(true); }
  async function submit(event: FormEvent) { event.preventDefault(); setSaving(true); try { if (editing) { await api(`/teams/${editing.id}`, { method: "PATCH", body: jsonBody({ name: form.name, description: form.description }) }); if (hasPermission("teams.manage_members")) await api(`/teams/${editing.id}/members`, { method: "PUT", body: jsonBody({ ids: form.member_ids }) }); } else { await api("/teams", { method: "POST", body: jsonBody(form) }); } setOpen(false); notify(editing ? "Team updated" : "Team created"); await reload(); } catch (reason) { notify((reason as Error).message, "error"); } finally { setSaving(false); } }
  return <>
    <PageHeader title="Teams" description="Teams connect people to one or more projects." actions={hasPermission("teams.create") ? <Button onClick={createDialog}><Plus />Create team</Button> : undefined} />
    {loading ? <LoadingState /> : error ? <ErrorState message={error} retry={reload} /> : data?.items.length ? <div className="content-grid">{data.items.map((team) => <Card key={team.id}><div className="split"><span className="metric-icon" style={{ position: "static" }}><Users /></span><Badge>{team.members.length} members</Badge></div><h2 style={{ marginTop: "1rem" }}>{team.name}</h2><p className="muted">{team.description || "No description provided."}</p><div className="profile-people">{team.members.slice(0, 8).map((member) => <UserIdentity key={member.id} user={member} compact linked />)}{team.members.length > 8 ? <Badge>+{team.members.length - 8}</Badge> : null}</div>{hasPermission("teams.edit") ? <div className="form-actions"><Button variant="outline" size="sm" onClick={() => editDialog(team)}>Manage team</Button></div> : null}</Card>)}</div> : <EmptyState title="No teams yet" description="Create a team to grant project access." />}
    <Dialog open={open} onOpenChange={setOpen} title={editing ? "Manage team" : "Create team"}><form className="form-grid" onSubmit={submit}><Field label="Name"><Input required autoFocus value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} /></Field><Field label="Description"><Textarea value={form.description} onChange={(event) => setForm({ ...form, description: event.target.value })} /></Field>{hasPermission("teams.manage_members") ? <Field label="Members"><SearchableMultiSelect options={users.data?.items.map((user) => ({ value: user.id, label: user.display_name, description: `@${user.username} · ${user.email}` })) ?? []} values={form.member_ids} onValuesChange={(member_ids) => setForm({ ...form, member_ids })} placeholder="Select members" searchPlaceholder="Search users…" /></Field> : null}<div className="dialog-actions"><Button type="button" variant="outline" onClick={() => setOpen(false)}>Cancel</Button><Button loading={saving}>{editing ? "Save changes" : "Create team"}</Button></div></form></Dialog>
  </>;
}
