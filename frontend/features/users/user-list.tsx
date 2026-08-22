"use client";

import { Pencil, Plus, UserRoundCheck, UserRoundX } from "lucide-react";
import { FormEvent, useState } from "react";

import { PageHeader } from "@/components/page-header";
import { UserIdentity } from "@/components/user-avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { Field, Input } from "@/components/ui/form";
import { SearchableMultiSelect } from "@/components/ui/searchable-select";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/states";
import { useToast } from "@/components/ui/toast";
import { useAuth } from "@/features/auth/auth-context";
import { useResource } from "@/hooks/use-resource";
import { formatDate } from "@/lib/utils";
import { api, jsonBody } from "@/services/api";
import type { Paginated, Role, User } from "@/types/api";

export function UserList() {
  const { user: current, hasPermission } = useAuth(); const { data, error, loading, reload } = useResource<Paginated<User>>("/users?page_size=100"); const roles = useResource<Role[]>(hasPermission("users.create") || hasPermission("users.edit") ? "/roles" : null); const { notify } = useToast();
  const blank = { username: "", email: "", first_name: "", last_name: "", password: "", role_ids: [] as string[], is_active: true };
  const [open, setOpen] = useState(false); const [saving, setSaving] = useState(false); const [editing, setEditing] = useState<User>(); const [form, setForm] = useState(blank);
  function createDialog() { setEditing(undefined); setForm(blank); setOpen(true); }
  function editDialog(user: User) { setEditing(user); setForm({ username: user.username, email: user.email, first_name: user.first_name, last_name: user.last_name, password: "", role_ids: user.roles.map((role) => role.id), is_active: user.is_active }); setOpen(true); }
  async function submit(event: FormEvent) { event.preventDefault(); setSaving(true); try { if (editing) { await api(`/users/${editing.id}`, { method: "PATCH", body: jsonBody({ username: form.username, email: form.email, first_name: form.first_name, last_name: form.last_name, role_ids: form.role_ids, is_active: form.is_active }) }); } else { await api("/users", { method: "POST", body: jsonBody(form) }); } setOpen(false); setForm(blank); notify(editing ? "User updated" : "User created"); await reload(); } catch (reason) { notify((reason as Error).message, "error"); } finally { setSaving(false); } }
  async function toggle(user: User) { try { await api(`/users/${user.id}`, { method: "PATCH", body: jsonBody({ is_active: !user.is_active }) }); notify(user.is_active ? "User disabled" : "User enabled"); await reload(); } catch (reason) { notify((reason as Error).message, "error"); } }
  return <>
    <PageHeader title="Users" description="Manage identities, status and role assignments." actions={hasPermission("users.create") ? <Button onClick={createDialog}><Plus />Create user</Button> : undefined} />
    {loading ? <LoadingState /> : error ? <ErrorState message={error} retry={reload} /> : data?.items.length ? <div className="table-wrap"><table><thead><tr><th>User</th><th>Email</th><th>Roles</th><th>Status</th><th>Last login</th><th><span className="sr-only">Actions</span></th></tr></thead><tbody>{data.items.map((user) => <tr key={user.id}><td><UserIdentity user={user} linked /></td><td>{user.email}</td><td><div className="inline-list">{user.roles.map((role) => <Badge key={role.id}>{role.name}</Badge>)}</div></td><td><Badge className={user.is_active ? "badge-success" : "badge-error"}>{user.is_active ? "Active" : "Disabled"}</Badge></td><td>{formatDate(user.last_login, true)}</td><td><div className="table-actions">{hasPermission("users.edit") ? <Button variant="ghost" size="icon" onClick={() => editDialog(user)} aria-label="Edit user"><Pencil /></Button> : null}{hasPermission("users.edit") && user.id !== current.id ? <Button variant="ghost" size="icon" onClick={() => toggle(user)} aria-label={user.is_active ? "Disable user" : "Enable user"}>{user.is_active ? <UserRoundX /> : <UserRoundCheck />}</Button> : null}</div></td></tr>)}</tbody></table></div> : <EmptyState title="No users" description="Create the first additional organization user." />}
    <Dialog open={open} onOpenChange={setOpen} title={editing ? "Edit user" : "Create user"} description={editing ? "Update identity, status and role assignments." : "The password can be changed later by the user."}><form className="form-grid" onSubmit={submit}><div className="form-grid two"><Field label="First name"><Input required autoFocus value={form.first_name} onChange={(event) => setForm({ ...form, first_name: event.target.value })} /></Field><Field label="Last name"><Input required value={form.last_name} onChange={(event) => setForm({ ...form, last_name: event.target.value })} /></Field><Field label="Username"><Input required minLength={3} value={form.username} onChange={(event) => setForm({ ...form, username: event.target.value })} /></Field><Field label="Email"><Input required type="email" value={form.email} onChange={(event) => setForm({ ...form, email: event.target.value })} /></Field></div>{!editing ? <Field label="Initial password" hint="At least 12 characters with upper, lower and numeric characters."><Input required minLength={12} type="password" autoComplete="new-password" value={form.password} onChange={(event) => setForm({ ...form, password: event.target.value })} /></Field> : null}<Field label="Roles" interactive><SearchableMultiSelect options={roles.data?.map((role) => ({ value: role.id, label: role.name, description: role.description ?? undefined })) ?? []} values={form.role_ids} onValuesChange={(role_ids) => setForm({ ...form, role_ids })} placeholder="Select roles" searchPlaceholder="Search roles…" /></Field>{editing ? <label className="user-chip"><input type="checkbox" checked={form.is_active} disabled={editing.id === current.id} onChange={(event) => setForm({ ...form, is_active: event.target.checked })} />Active account</label> : null}<div className="dialog-actions"><Button type="button" variant="outline" onClick={() => setOpen(false)}>Cancel</Button><Button loading={saving}>{editing ? "Save changes" : "Create user"}</Button></div></form></Dialog>
  </>;
}
