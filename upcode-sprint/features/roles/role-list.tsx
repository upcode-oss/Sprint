"use client";

import { Plus, ShieldCheck } from "lucide-react";
import { FormEvent, useState } from "react";

import { PageHeader } from "@/components/page-header";
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
import type { Permission, Role } from "@/types/api";

export function RoleList() {
  const { hasPermission } = useAuth(); const roles = useResource<Role[]>("/roles"); const permissions = useResource<Permission[]>("/permissions"); const { notify } = useToast(); const [open, setOpen] = useState(false); const [saving, setSaving] = useState(false); const [form, setForm] = useState({ name: "", description: "", permission_keys: [] as string[] });
  async function submit(event: FormEvent) { event.preventDefault(); setSaving(true); try { await api("/roles", { method: "POST", body: jsonBody(form) }); setOpen(false); setForm({ name: "", description: "", permission_keys: [] }); notify("Role created"); await roles.reload(); } catch (reason) { notify((reason as Error).message, "error"); } finally { setSaving(false); } }
  return <><PageHeader title="Roles & permissions" description="Effective access is the union of every assigned role." actions={hasPermission("roles.create") ? <Button onClick={() => setOpen(true)}><Plus />Create role</Button> : undefined} />{roles.loading ? <LoadingState /> : roles.error ? <ErrorState message={roles.error} retry={roles.reload} /> : roles.data?.length ? <div className="content-grid">{roles.data.map((role) => <Card key={role.id}><div className="split"><span className="metric-icon" style={{ position: "static" }}><ShieldCheck /></span>{role.is_system ? <Badge className="badge-info">System</Badge> : null}</div><h2 style={{ marginTop: "1rem" }}>{role.name}</h2><p className="muted">{role.description || "No description."}</p><div className="inline-list">{role.permissions.slice(0, 8).map((permission) => <Badge className="mono" key={permission.id}>{permission.key}</Badge>)}{role.permissions.length > 8 ? <Badge>+{role.permissions.length - 8}</Badge> : null}</div></Card>)}</div> : <EmptyState title="No roles" description="The Admin role is created during setup." />}<Dialog open={open} onOpenChange={setOpen} title="Create role"><form className="form-grid" onSubmit={submit}><Field label="Name"><Input required autoFocus value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} /></Field><Field label="Description"><Textarea value={form.description} onChange={(event) => setForm({ ...form, description: event.target.value })} /></Field><Field label="Permissions" interactive><SearchableMultiSelect options={permissions.data?.map((permission) => ({ value: permission.key, label: permission.key, description: permission.description })) ?? []} values={form.permission_keys} onValuesChange={(permission_keys) => setForm({ ...form, permission_keys })} placeholder="Select permissions" searchPlaceholder="Search permissions…" /></Field><div className="dialog-actions"><Button type="button" variant="outline" onClick={() => setOpen(false)}>Cancel</Button><Button loading={saving}>Create role</Button></div></form></Dialog></>;
}
