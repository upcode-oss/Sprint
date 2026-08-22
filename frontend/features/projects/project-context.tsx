"use client";

import { createContext, useContext } from "react";
import { useParams, usePathname } from "next/navigation";
import Link from "next/link";

import { PageHeader } from "@/components/page-header";
import { Badge } from "@/components/ui/badge";
import { ErrorState, LoadingState } from "@/components/ui/states";
import { useResource } from "@/hooks/use-resource";
import type { Project } from "@/types/api";

type Value = { project: Project; reload: () => Promise<void> };
const ProjectContext = createContext<Value | null>(null);
const tabs = [
  ["Overview", ""], ["Kanban", "/kanban"], ["Activity", "/activity"], ["Scrum", "/scrum"], ["Documents", "/documents"], ["Meetings", "/meetings"], ["Members", "/members"], ["Settings", "/settings"],
];

export function ProjectFrame({ children }: { children: React.ReactNode }) {
  const params = useParams<{ projectId: string }>(); const pathname = usePathname(); const resource = useResource<Project>(params.projectId ? `/projects/${params.projectId}` : null);
  if (resource.loading) return <LoadingState label="Loading project…" />;
  if (resource.error || !resource.data) return <ErrorState message={resource.error ?? "Project not found"} retry={resource.reload} />;
  const base = `/projects/${resource.data.id}`;
  return <ProjectContext.Provider value={{ project: resource.data, reload: resource.reload }}><PageHeader title={resource.data.name} description={`${resource.data.key} · ${resource.data.description || "No project description"}`} actions={<Badge className={resource.data.status === "active" ? "badge-success" : ""}>{resource.data.status}</Badge>} /><nav className="project-tabs" aria-label="Project navigation">{tabs.map(([label, suffix]) => { const href = `${base}${suffix}`; const active = suffix ? pathname.startsWith(href) : pathname === base; return <Link className={`project-tab ${active ? "active" : ""}`} href={href} key={label}>{label}</Link>; })}</nav>{children}</ProjectContext.Provider>;
}

export function useProject() { const value = useContext(ProjectContext); if (!value) throw new Error("useProject requires ProjectFrame"); return value; }
