"use client";

import { Users } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/states";
import { useProject } from "@/features/projects/project-context";
import { useResource } from "@/hooks/use-resource";
import { initials } from "@/lib/utils";
import type { UserBrief } from "@/types/api";

export default function ProjectMembersPage() {
  const { project } = useProject(); const { data, error, loading, reload } = useResource<UserBrief[]>(`/projects/${project.id}/members`);
  if (loading) return <LoadingState />; if (error) return <ErrorState message={error} retry={reload} />;
  return <><div className="page-header"><div><h2>Project members</h2><p>Derived from all teams assigned to this project; duplicate users are merged.</p></div><Badge><Users />{data?.length ?? 0}</Badge></div>{data?.length ? <div className="content-grid">{data.map((member) => <Card key={member.id}><div className="user-chip"><span className="avatar">{initials(member.first_name, member.last_name)}</span><div><strong>{member.first_name} {member.last_name}</strong><span>@{member.username}</span></div></div></Card>)}</div> : <EmptyState title="No project members" description="Assign a team in project settings." />}</>;
}

