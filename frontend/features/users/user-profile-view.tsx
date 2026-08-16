"use client";

import { Building2, Mail, Pencil, Phone, Smartphone, Upload, Users } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { ChangeEvent, FormEvent, useState } from "react";

import { PageHeader } from "@/components/page-header";
import { UserAvatar, presenceLabels } from "@/components/user-avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardHeader } from "@/components/ui/card";
import { Dialog } from "@/components/ui/dialog";
import { Field, Input, Textarea } from "@/components/ui/form";
import { ErrorState, LoadingState } from "@/components/ui/states";
import { useToast } from "@/components/ui/toast";
import { useAuth } from "@/features/auth/auth-context";
import { ContactManager } from "@/features/users/profile-manager";
import { useResource } from "@/hooks/use-resource";
import { api, jsonBody } from "@/services/api";
import type { UserContact, UserProfile } from "@/types/api";

export function UserProfileView() {
  const { userId } = useParams<{ userId: string }>(); const { hasPermission } = useAuth(); const { notify } = useToast();
  const profile = useResource<UserProfile>(`/users/${userId}`);
  const mayManageContacts = hasPermission("users.contacts.view") && hasPermission("users.contacts.edit");
  const contacts = useResource<UserContact[]>(mayManageContacts ? `/users/${userId}/contacts` : null);
  const [open, setOpen] = useState(false); const [saving, setSaving] = useState(false);
  const [form, setForm] = useState({ first_name: "", last_name: "", display_name: "", job_title: "", department: "", bio: "" });
  function edit() { if (!profile.data) return; setForm({ first_name: profile.data.first_name, last_name: profile.data.last_name, display_name: profile.data.display_name, job_title: profile.data.job_title ?? "", department: profile.data.department ?? "", bio: profile.data.bio ?? "" }); setOpen(true); }
  async function save(event: FormEvent) { event.preventDefault(); setSaving(true); try { await api(`/users/${userId}/profile`, { method: "PATCH", body: jsonBody(form) }); setOpen(false); notify("User profile updated"); await profile.reload(); } catch (reason) { notify((reason as Error).message, "error"); } finally { setSaving(false); } }
  async function uploadAvatar(event: ChangeEvent<HTMLInputElement>) { const file = event.target.files?.[0]; if (!file) return; const body = new FormData(); body.set("avatar", file); setSaving(true); try { await api(`/users/${userId}/avatar`, { method: "POST", body }); notify("Profile picture updated"); await profile.reload(); } catch (reason) { notify((reason as Error).message, "error"); } finally { setSaving(false); event.target.value = ""; } }
  if (profile.loading) return <LoadingState label="Loading user profile…" />;
  if (profile.error || !profile.data) return <ErrorState message={profile.error ?? "Profile unavailable"} retry={profile.reload} />;
  const user = profile.data; const icons = { email: Mail, phone: Phone, mobile: Smartphone };
  return <>
    <PageHeader title={user.display_name} description={`@${user.username}`} actions={hasPermission("users.profile.edit") ? <div className="page-actions"><label className="button button-outline button-default"><Upload />Avatar<input className="sr-only" type="file" accept="image/jpeg,image/png,image/webp" onChange={uploadAvatar} disabled={saving} /></label><Button onClick={edit}><Pencil />Edit profile</Button></div> : undefined} />
    <Card className="profile-hero"><UserAvatar user={user} size={96} /><div><h2>{user.display_name}</h2><p>{user.job_title || "No job title"}{user.department ? ` · ${user.department}` : ""}</p><div className="inline-list"><Badge className={`presence-label presence-${user.presence.status}`}>{presenceLabels[user.presence.status]}</Badge>{user.presence.status_message ? <Badge>{user.presence.status_message}</Badge> : null}</div></div></Card>
    <div className="content-grid profile-grid">
      <Card><CardHeader title="About" />{user.bio ? <p>{user.bio}</p> : <p className="muted">No biography provided.</p>}{user.department ? <p className="small"><Building2 /> {user.department}</p> : null}</Card>
      <Card><CardHeader title="Contact information" description="Only entries visible to you are returned by the server." />{user.contacts.length ? <div className="contact-list">{user.contacts.map((contact) => { const Icon = icons[contact.type]; return <div className="contact-row" key={contact.id}><Icon /><div><strong>{contact.value}</strong><div className="inline-list"><span className="muted small">{contact.label}</span>{contact.is_primary ? <Badge className="badge-success">Primary</Badge> : null}<Badge>{contact.visibility}</Badge></div></div></div>; })}</div> : <p className="muted">No contact information is visible.</p>}</Card>
      <Card><CardHeader title="Teams" action={<Users />} />{user.teams.length ? <div className="inline-list">{user.teams.map((team) => <Badge key={team.id}>{team.name}</Badge>)}</div> : <p className="muted">No shared teams.</p>}</Card>
      <Card><CardHeader title="Projects" />{user.projects.length ? <div className="stack">{user.projects.map((project) => <Link className="split" href={`/projects/${project.id}`} key={project.id}><strong>{project.name}</strong><span>→</span></Link>)}</div> : <p className="muted">No shared projects.</p>}</Card>
      {mayManageContacts ? <ContactManager contacts={contacts} basePath={`/users/${userId}`} /> : null}
    </div>
    <Dialog open={open} onOpenChange={setOpen} title="Edit user profile" description="Account username and primary email remain protected."><form className="form-grid" onSubmit={save}><div className="form-grid two"><Field label="First name"><Input required value={form.first_name} onChange={(event) => setForm({ ...form, first_name: event.target.value })} /></Field><Field label="Last name"><Input required value={form.last_name} onChange={(event) => setForm({ ...form, last_name: event.target.value })} /></Field><Field label="Display name"><Input value={form.display_name} onChange={(event) => setForm({ ...form, display_name: event.target.value })} /></Field><Field label="Job title"><Input value={form.job_title} onChange={(event) => setForm({ ...form, job_title: event.target.value })} /></Field><Field label="Department"><Input value={form.department} onChange={(event) => setForm({ ...form, department: event.target.value })} /></Field></div><Field label="Bio"><Textarea value={form.bio} onChange={(event) => setForm({ ...form, bio: event.target.value })} /></Field><div className="dialog-actions"><Button type="button" variant="outline" onClick={() => setOpen(false)}>Cancel</Button><Button loading={saving}>Save profile</Button></div></form></Dialog>
  </>;
}
