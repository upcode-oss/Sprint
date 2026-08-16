"use client";

import { Bell, KeyRound, Mail, Pencil, Phone, Plus, Save, Smartphone, Trash2, Upload } from "lucide-react";
import { ChangeEvent, FormEvent, useEffect, useState } from "react";

import { PageHeader } from "@/components/page-header";
import { UserAvatar, presenceLabels } from "@/components/user-avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardHeader } from "@/components/ui/card";
import { ConfirmDialog, Dialog } from "@/components/ui/dialog";
import { Field, Input, Select, Textarea } from "@/components/ui/form";
import { ErrorState, LoadingState } from "@/components/ui/states";
import { useToast } from "@/components/ui/toast";
import { useAuth } from "@/features/auth/auth-context";
import { useResource } from "@/hooks/use-resource";
import { formatDate } from "@/lib/utils";
import { api, jsonBody } from "@/services/api";
import type { ContactType, ContactVisibility, Presence, PresenceStatus, UserContact } from "@/types/api";

const timezones = ["UTC", "Europe/Vienna", "Europe/Berlin", "Europe/London", "America/New_York", "America/Los_Angeles", "Asia/Tokyo"];
const blankContact = { type: "email" as ContactType, label: "Business", value: "", is_primary: false, visibility: "private" as ContactVisibility };

export function ProfileManager() {
  const { user, reload } = useAuth();
  const { notify } = useToast();
  const contacts = useResource<UserContact[]>("/users/me/contacts");
  const presence = useResource<Presence>("/users/me/presence");
  const [saving, setSaving] = useState(false);
  const [profile, setProfile] = useState({
    first_name: user.first_name,
    last_name: user.last_name,
    display_name: user.display_name === `${user.first_name} ${user.last_name}` ? "" : user.display_name,
    job_title: user.job_title ?? "",
    department: user.department ?? "",
    bio: user.bio ?? "",
    timezone: user.timezone,
    locale: user.locale ?? "",
  });
  const [passwords, setPasswords] = useState({ current_password: "", password: "" });

  async function saveProfile(event: FormEvent) {
    event.preventDefault(); setSaving(true);
    try {
      await api("/users/me", { method: "PATCH", body: jsonBody({ ...profile, locale: profile.locale || null }) });
      await reload(); notify("Profile updated");
    } catch (reason) { notify((reason as Error).message, "error"); }
    finally { setSaving(false); }
  }

  async function uploadAvatar(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    const body = new FormData(); body.set("avatar", file); setSaving(true);
    try { await api("/users/me/avatar", { method: "POST", body }); await reload(); notify("Profile picture updated"); }
    catch (reason) { notify((reason as Error).message, "error"); }
    finally { setSaving(false); event.target.value = ""; }
  }

  async function deleteAvatar() {
    setSaving(true);
    try { await api("/users/me/avatar", { method: "DELETE" }); await reload(); notify("Profile picture removed"); }
    catch (reason) { notify((reason as Error).message, "error"); }
    finally { setSaving(false); }
  }

  async function savePassword(event: FormEvent) {
    event.preventDefault(); setSaving(true);
    try {
      await api("/auth/change-password", { method: "POST", body: jsonBody(passwords) });
      setPasswords({ current_password: "", password: "" }); notify("Password changed");
    } catch (reason) { notify((reason as Error).message, "error"); }
    finally { setSaving(false); }
  }

  return <>
    <PageHeader title="Profile" description={`Manage profile, contact information and availability for @${user.username}.`} />
    <Card className="profile-hero">
      <UserAvatar user={user} size={88} />
      <div><h2>{user.display_name}</h2><p>{user.job_title || "No job title"}{user.department ? ` · ${user.department}` : ""}</p><div className="inline-list"><Badge className={`presence-label presence-${user.presence.status}`}>{presenceLabels[user.presence.status]}</Badge><Badge>@{user.username}</Badge></div></div>
      <div className="profile-avatar-actions"><label className="button button-outline button-default" aria-label="Upload profile picture"><Upload />Upload<input className="sr-only" type="file" accept="image/jpeg,image/png,image/webp" onChange={uploadAvatar} disabled={saving} /></label>{user.avatar_url ? <Button type="button" variant="ghost" onClick={deleteAvatar} disabled={saving}>Remove</Button> : null}<span className="muted small">JPEG, PNG or WebP · configured size limit</span></div>
    </Card>
    <div className="content-grid profile-grid">
      <Card><CardHeader title="Profile" description="Public organization profile information." /><form className="form-grid" onSubmit={saveProfile}><div className="form-grid two"><Field label="First name"><Input required value={profile.first_name} onChange={(event) => setProfile({ ...profile, first_name: event.target.value })} /></Field><Field label="Last name"><Input required value={profile.last_name} onChange={(event) => setProfile({ ...profile, last_name: event.target.value })} /></Field><Field label="Display name" hint="Optional; first and last name are used as fallback."><Input value={profile.display_name} onChange={(event) => setProfile({ ...profile, display_name: event.target.value })} /></Field><Field label="Job title"><Input value={profile.job_title} onChange={(event) => setProfile({ ...profile, job_title: event.target.value })} /></Field><Field label="Department"><Input value={profile.department} onChange={(event) => setProfile({ ...profile, department: event.target.value })} /></Field><Field label="Primary email" hint="Account field; administrators manage changes."><Input readOnly type="email" value={user.email} /></Field></div><Field label="Bio"><Textarea maxLength={5000} value={profile.bio} onChange={(event) => setProfile({ ...profile, bio: event.target.value })} /></Field><div className="form-actions"><Button loading={saving}><Save />Save profile</Button></div></form></Card>
      <PresenceCard resource={presence} />
      <ContactManager contacts={contacts} basePath="/users/me" />
      <Card><CardHeader title="Preferences" description="Language and local date/time context." /><form className="form-grid" onSubmit={saveProfile}><Field label="Timezone"><Select value={profile.timezone} onChange={(event) => setProfile({ ...profile, timezone: event.target.value })}>{timezones.map((timezone) => <option key={timezone} value={timezone}>{timezone}</option>)}</Select></Field><Field label="Language"><Select value={profile.locale} onChange={(event) => setProfile({ ...profile, locale: event.target.value })}><option value="">System default</option><option value="de-AT">Deutsch (Österreich)</option><option value="de-DE">Deutsch (Deutschland)</option><option value="en-US">English (US)</option><option value="en-GB">English (UK)</option></Select></Field><div className="form-actions"><Button loading={saving}><Save />Save preferences</Button></div></form></Card>
      <Card><CardHeader title="Security" description="Changing the password revokes other sessions." action={<KeyRound />} /><form className="form-grid" onSubmit={savePassword}><Field label="Current password"><Input required type="password" autoComplete="current-password" value={passwords.current_password} onChange={(event) => setPasswords({ ...passwords, current_password: event.target.value })} /></Field><Field label="New password" hint="At least 12 characters with upper, lower and numeric characters."><Input required minLength={12} type="password" autoComplete="new-password" value={passwords.password} onChange={(event) => setPasswords({ ...passwords, password: event.target.value })} /></Field><div className="form-actions"><Button loading={saving}><KeyRound />Change password</Button></div></form></Card>
    </div>
  </>;
}

export function ContactManager({ contacts, basePath }: { contacts: ReturnType<typeof useResource<UserContact[]>>; basePath: string }) {
  const { notify } = useToast(); const [open, setOpen] = useState(false); const [editing, setEditing] = useState<UserContact>(); const [removing, setRemoving] = useState<UserContact>(); const [saving, setSaving] = useState(false); const [form, setForm] = useState(blankContact);
  function add() { setEditing(undefined); setForm(blankContact); setOpen(true); }
  function edit(contact: UserContact) { setEditing(contact); setForm({ type: contact.type, label: contact.label, value: contact.value, is_primary: contact.is_primary, visibility: contact.visibility }); setOpen(true); }
  async function submit(event: FormEvent) { event.preventDefault(); setSaving(true); try { await api(editing ? `${basePath}/contacts/${editing.id}` : `${basePath}/contacts`, { method: editing ? "PATCH" : "POST", body: jsonBody(form) }); setOpen(false); notify(editing ? "Contact updated" : "Contact added"); await contacts.reload(); } catch (reason) { notify((reason as Error).message, "error"); } finally { setSaving(false); } }
  async function remove() { if (!removing) return; setSaving(true); try { await api(`${basePath}/contacts/${removing.id}`, { method: "DELETE" }); setRemoving(undefined); notify("Contact deleted"); await contacts.reload(); } catch (reason) { notify((reason as Error).message, "error"); } finally { setSaving(false); } }
  const icons = { email: Mail, phone: Phone, mobile: Smartphone };
  return <Card className="wide"><CardHeader title="Contact information" description="Add multiple email addresses and phone numbers with individual visibility." action={<Button size="sm" onClick={add}><Plus />Add contact</Button>} />{contacts.loading ? <LoadingState label="Loading contacts…" /> : contacts.error ? <ErrorState message={contacts.error} retry={contacts.reload} /> : contacts.data?.length ? <div className="contact-list">{contacts.data.map((contact) => { const Icon = icons[contact.type]; return <div className="contact-row" key={contact.id}><span className="metric-icon" style={{ position: "static" }}><Icon /></span><div><strong>{contact.value}</strong><div className="inline-list"><span className="muted small">{contact.label}</span>{contact.is_primary ? <Badge className="badge-success">Primary</Badge> : null}<Badge>{contact.visibility}</Badge></div></div><div className="table-actions"><Button variant="ghost" size="icon" onClick={() => edit(contact)} aria-label="Edit contact"><Pencil /></Button><Button variant="ghost" size="icon" onClick={() => setRemoving(contact)} aria-label="Delete contact"><Trash2 /></Button></div></div>; })}</div> : <p className="muted">No additional contact information.</p>}<Dialog open={open} onOpenChange={setOpen} title={editing ? "Edit contact" : "Add contact"}><form className="form-grid" onSubmit={submit}><div className="form-grid two"><Field label="Type"><Select value={form.type} onChange={(event) => setForm({ ...form, type: event.target.value as ContactType })}><option value="email">Email</option><option value="phone">Phone</option><option value="mobile">Mobile</option></Select></Field><Field label="Label"><Input required value={form.label} onChange={(event) => setForm({ ...form, label: event.target.value })} /></Field></div><Field label="Value"><Input required type={form.type === "email" ? "email" : "tel"} value={form.value} onChange={(event) => setForm({ ...form, value: event.target.value })} /></Field><Field label="Visibility"><Select value={form.visibility} onChange={(event) => setForm({ ...form, visibility: event.target.value as ContactVisibility })}><option value="private">Private</option><option value="teams">Shared teams</option><option value="organization">Organization</option></Select></Field><label className="user-chip"><input type="checkbox" checked={form.is_primary} onChange={(event) => setForm({ ...form, is_primary: event.target.checked })} />Primary contact for this type</label><div className="dialog-actions"><Button type="button" variant="outline" onClick={() => setOpen(false)}>Cancel</Button><Button loading={saving}>Save contact</Button></div></form></Dialog><ConfirmDialog open={Boolean(removing)} onOpenChange={(value) => !value && setRemoving(undefined)} title="Delete contact information?" description="This contact entry will be permanently removed." onConfirm={remove} loading={saving} /></Card>;
}

function PresenceCard({ resource }: { resource: ReturnType<typeof useResource<Presence>> }) {
  const { notify } = useToast(); const [saving, setSaving] = useState(false); const [form, setForm] = useState({ status: "" as PresenceStatus | "", status_message: "", status_until: "" });
  useEffect(() => { if (resource.data) setForm({ status: resource.data.manual_status ?? "", status_message: resource.data.status_message ?? "", status_until: resource.data.status_until?.slice(0, 16) ?? "" }); }, [resource.data]);
  async function submit(event: FormEvent) { event.preventDefault(); setSaving(true); try { await api("/users/me/presence", { method: "PATCH", body: jsonBody({ status: form.status || null, status_message: form.status_message || null, status_until: form.status_until ? new Date(form.status_until).toISOString() : null }) }); notify("Availability updated"); await resource.reload(); } catch (reason) { notify((reason as Error).message, "error"); } finally { setSaving(false); } }
  return <Card><CardHeader title="Presence" description="Manual status takes precedence over activity detection." action={<Bell />} />{resource.loading ? <LoadingState label="Loading presence…" /> : resource.error ? <ErrorState message={resource.error} retry={resource.reload} /> : <form className="form-grid" onSubmit={submit}><Field label="Status"><Select value={form.status} onChange={(event) => setForm({ ...form, status: event.target.value as PresenceStatus | "" })}><option value="">Automatic</option>{Object.entries(presenceLabels).map(([value, label]) => <option value={value} key={value}>{label}</option>)}</Select></Field><Field label="Status message"><Input maxLength={280} placeholder="e.g. In a meeting" value={form.status_message} onChange={(event) => setForm({ ...form, status_message: event.target.value })} /></Field><Field label="Status until" hint="After this time the manual status is cleared automatically."><Input type="datetime-local" value={form.status_until} onChange={(event) => setForm({ ...form, status_until: event.target.value })} /></Field>{resource.data?.last_seen_at ? <p className="muted small">Last activity: {formatDate(resource.data.last_seen_at, true)}</p> : null}<div className="form-actions"><Button loading={saving}><Save />Save presence</Button></div></form>}</Card>;
}
