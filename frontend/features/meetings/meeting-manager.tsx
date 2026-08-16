"use client";

import { CalendarPlus, ExternalLink, MapPin, Users } from "lucide-react";
import { FormEvent, useState } from "react";

import { PageHeader } from "@/components/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Dialog } from "@/components/ui/dialog";
import { Field, Input, Select, Textarea } from "@/components/ui/form";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/states";
import { useToast } from "@/components/ui/toast";
import { useAuth } from "@/features/auth/auth-context";
import { useResource } from "@/hooks/use-resource";
import { formatDate } from "@/lib/utils";
import { api, jsonBody } from "@/services/api";
import type { Meeting, Paginated, Project, Team, UserBrief } from "@/types/api";

const blank = {
  title: "",
  description: "",
  start: "",
  end: "",
  location: "",
  meeting_url: "",
  scope_type: "personal",
  scope_id: "",
  participant_ids: [] as string[],
};

export function MeetingManager() {
  const { hasPermission } = useAuth();
  const { notify } = useToast();
  const meetings = useResource<Meeting[]>("/meetings");
  const teams = useResource<Paginated<Team>>("/teams?page_size=100");
  const projects = useResource<Paginated<Project>>("/projects?page_size=100");
  const [open, setOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState(blank);
  const participantQuery = open
    ? `/meetings/available-participants?scope_type=${form.scope_type}${form.scope_id ? `&scope_id=${form.scope_id}` : ""}`
    : null;
  const participants = useResource<UserBrief[]>(participantQuery);

  async function create(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    try {
      await api("/meetings", {
        method: "POST",
        body: jsonBody({
          ...form,
          start: new Date(form.start).toISOString(),
          end: new Date(form.end).toISOString(),
          meeting_url: form.meeting_url || null,
          scope_id: ["team", "project"].includes(form.scope_type) ? form.scope_id : null,
        }),
      });
      setOpen(false);
      setForm(blank);
      notify("Meeting scheduled");
      await meetings.reload();
    } catch (reason) {
      notify((reason as Error).message, "error");
    } finally {
      setSaving(false);
    }
  }

  return <>
    <PageHeader title="Meetings" description="Meetings appear once for every invited participant through calendar aggregation." actions={hasPermission("meetings.create") ? <Button onClick={() => setOpen(true)}><CalendarPlus />Schedule meeting</Button> : undefined} />
    {meetings.loading ? <LoadingState label="Loading meetings…" /> : meetings.error ? <ErrorState message={meetings.error} retry={meetings.reload} /> : meetings.data?.length ? <div className="content-grid">{meetings.data.map((meeting) => <Card key={meeting.id}><div className="split"><Badge>{meeting.scope_type}</Badge><Badge>{formatDate(meeting.start, true)}</Badge></div><h2 style={{ marginTop: "1rem" }}>{meeting.title}</h2><p className="muted">{meeting.description || "No agenda provided."}</p>{meeting.location ? <p><MapPin /> {meeting.location}</p> : null}<div className="inline-list">{meeting.participants.map((participant) => <Badge key={participant.user.id}>{participant.user.first_name} {participant.user.last_name}</Badge>)}</div>{meeting.meeting_url ? <div className="form-actions"><Button asChild variant="outline" size="sm"><a href={meeting.meeting_url} target="_blank" rel="noreferrer"><ExternalLink />Join</a></Button></div> : null}</Card>)}</div> : <EmptyState title="No meetings" description="Schedule a personal, team, project or organization meeting." />}
    <Dialog open={open} onOpenChange={setOpen} title="Schedule meeting" description="Participant choices are restricted to the selected scope."><form className="form-grid" onSubmit={create}><Field label="Title"><Input required autoFocus value={form.title} onChange={(event) => setForm({ ...form, title: event.target.value })} /></Field><Field label="Agenda"><Textarea value={form.description} onChange={(event) => setForm({ ...form, description: event.target.value })} /></Field><div className="form-grid two"><Field label="Start"><Input required type="datetime-local" value={form.start} onChange={(event) => setForm({ ...form, start: event.target.value })} /></Field><Field label="End"><Input required type="datetime-local" value={form.end} onChange={(event) => setForm({ ...form, end: event.target.value })} /></Field><Field label="Scope"><Select value={form.scope_type} onChange={(event) => setForm({ ...form, scope_type: event.target.value, scope_id: "", participant_ids: [] })}><option value="personal">Personal</option><option value="organization">Organization</option><option value="team">Team</option><option value="project">Project</option></Select></Field>{form.scope_type === "team" ? <Field label="Team"><Select required value={form.scope_id} onChange={(event) => setForm({ ...form, scope_id: event.target.value, participant_ids: [] })}><option value="">Select a team</option>{teams.data?.items.map((team) => <option key={team.id} value={team.id}>{team.name}</option>)}</Select></Field> : form.scope_type === "project" ? <Field label="Project"><Select required value={form.scope_id} onChange={(event) => setForm({ ...form, scope_id: event.target.value, participant_ids: [] })}><option value="">Select a project</option>{projects.data?.items.map((project) => <option key={project.id} value={project.id}>{project.name}</option>)}</Select></Field> : null}<Field label="Location"><Input value={form.location} onChange={(event) => setForm({ ...form, location: event.target.value })} /></Field><Field label="Meeting URL"><Input type="url" value={form.meeting_url} onChange={(event) => setForm({ ...form, meeting_url: event.target.value })} /></Field></div><Field label="Participants" hint={participants.loading ? "Loading eligible users…" : "The creator is included automatically."}><Select multiple disabled={participants.loading || (["team", "project"].includes(form.scope_type) && !form.scope_id)} value={form.participant_ids} onChange={(event) => setForm({ ...form, participant_ids: Array.from(event.target.selectedOptions, (option) => option.value) })}>{participants.data?.map((user) => <option key={user.id} value={user.id}>{user.first_name} {user.last_name} (@{user.username})</option>)}</Select></Field><div className="dialog-actions"><Button type="button" variant="outline" onClick={() => setOpen(false)}>Cancel</Button><Button loading={saving}><Users />Schedule meeting</Button></div></form></Dialog>
  </>;
}

