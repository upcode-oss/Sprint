"use client";

import { CalendarPlus, ExternalLink, MapPin, Users } from "lucide-react";
import { FormEvent, useMemo, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Dialog } from "@/components/ui/dialog";
import { Field, Input, Select, Textarea } from "@/components/ui/form";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/states";
import { useToast } from "@/components/ui/toast";
import { UserIdentity } from "@/components/user-avatar";
import { useAuth } from "@/features/auth/auth-context";
import { useProject } from "@/features/projects/project-context";
import { useResource } from "@/hooks/use-resource";
import { formatDate } from "@/lib/utils";
import { api, jsonBody } from "@/services/api";
import type { Meeting, UserBrief } from "@/types/api";

export function ProjectMeetingList() {
  const { project } = useProject(); const { hasPermission } = useAuth(); const meetings = useResource<Meeting[]>("/meetings?scope_type=project"); const members = useResource<UserBrief[]>(`/projects/${project.id}/members`); const { notify } = useToast(); const [open, setOpen] = useState(false); const [saving, setSaving] = useState(false); const [form, setForm] = useState({ title: "", description: "", start: "", end: "", location: "", meeting_url: "", participant_ids: [] as string[] });
  const filtered = useMemo(() => meetings.data?.filter((meeting) => meeting.scope_id === project.id) ?? [], [meetings.data, project.id]);
  async function create(event: FormEvent) { event.preventDefault(); setSaving(true); try { await api("/meetings", { method: "POST", body: jsonBody({ ...form, start: new Date(form.start).toISOString(), end: new Date(form.end).toISOString(), meeting_url: form.meeting_url || null, scope_type: "project", scope_id: project.id }) }); setOpen(false); setForm({ title: "", description: "", start: "", end: "", location: "", meeting_url: "", participant_ids: [] }); notify("Meeting scheduled"); await meetings.reload(); } catch (reason) { notify((reason as Error).message, "error"); } finally { setSaving(false); } }
  if (meetings.loading) return <LoadingState label="Loading meetings…" />; if (meetings.error) return <ErrorState message={meetings.error} retry={meetings.reload} />;
  return <><div className="page-header"><div><h2>Project meetings</h2><p>Invited participants see these meetings in their combined calendars.</p></div>{hasPermission("meetings.create") ? <Button onClick={() => setOpen(true)}><CalendarPlus />Schedule meeting</Button> : null}</div>{filtered.length ? <div className="content-grid">{filtered.map((meeting) => <Card key={meeting.id}><div className="split"><Badge>{formatDate(meeting.start, true)}</Badge><Badge>{meeting.participants.length} invited</Badge></div><h2 style={{ marginTop: "1rem" }}>{meeting.title}</h2><p className="muted">{meeting.description || "No agenda provided."}</p>{meeting.location ? <p className="small"><MapPin /> {meeting.location}</p> : null}<div className="profile-people">{meeting.participants.map((participant) => <UserIdentity key={participant.user.id} user={participant.user} compact linked />)}</div>{meeting.meeting_url ? <div className="form-actions"><Button asChild variant="outline" size="sm"><a href={meeting.meeting_url} target="_blank" rel="noreferrer"><ExternalLink />Join meeting</a></Button></div> : null}</Card>)}</div> : <EmptyState title="No project meetings" description="Schedule planning, reviews or any team conversation." />}<Dialog open={open} onOpenChange={setOpen} title="Schedule project meeting"><form className="form-grid" onSubmit={create}><Field label="Title"><Input required autoFocus value={form.title} onChange={(event) => setForm({ ...form, title: event.target.value })} /></Field><Field label="Description / agenda"><Textarea value={form.description} onChange={(event) => setForm({ ...form, description: event.target.value })} /></Field><div className="form-grid two"><Field label="Start"><Input required type="datetime-local" value={form.start} onChange={(event) => setForm({ ...form, start: event.target.value })} /></Field><Field label="End"><Input required type="datetime-local" value={form.end} onChange={(event) => setForm({ ...form, end: event.target.value })} /></Field><Field label="Location"><Input value={form.location} onChange={(event) => setForm({ ...form, location: event.target.value })} /></Field><Field label="Meeting URL"><Input type="url" value={form.meeting_url} onChange={(event) => setForm({ ...form, meeting_url: event.target.value })} /></Field></div><Field label="Participants" hint="Only project members are selectable."><Select multiple required value={form.participant_ids} onChange={(event) => setForm({ ...form, participant_ids: Array.from(event.target.selectedOptions, (option) => option.value) })}>{members.data?.map((member) => <option value={member.id} key={member.id}>{member.display_name}</option>)}</Select></Field><div className="dialog-actions"><Button type="button" variant="outline" onClick={() => setOpen(false)}>Cancel</Button><Button loading={saving}><Users />Schedule meeting</Button></div></form></Dialog></>;
}
