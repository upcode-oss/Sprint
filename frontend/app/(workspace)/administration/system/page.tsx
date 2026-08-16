"use client";

import { Database, Server, ShieldCheck } from "lucide-react";

import { PageHeader } from "@/components/page-header";
import { Badge } from "@/components/ui/badge";
import { Card, CardHeader } from "@/components/ui/card";
import { ErrorState, LoadingState } from "@/components/ui/states";
import { useResource } from "@/hooks/use-resource";

type Info = { version: string; environment: string; database_engine: string; setup_completed: boolean };
export default function SystemPage() {
  const { data, error, loading, reload } = useResource<Info>("/settings/system");
  return <><PageHeader title="System" description="Runtime and installation status without sensitive configuration values." />{loading ? <LoadingState /> : error || !data ? <ErrorState message={error ?? "System information unavailable"} retry={reload} /> : <div className="metrics-grid"><Card className="metric"><span className="metric-label">Version</span><strong className="metric-value mono">{data.version}</strong><span className="metric-icon"><Server /></span></Card><Card className="metric"><span className="metric-label">Environment</span><strong className="metric-value" style={{ fontSize: "1.1rem" }}>{data.environment}</strong><span className="metric-icon"><ShieldCheck /></span></Card><Card className="metric"><span className="metric-label">Database</span><strong className="metric-value" style={{ fontSize: "1.1rem" }}>{data.database_engine}</strong><span className="metric-icon"><Database /></span></Card><Card><CardHeader title="Installation" /><Badge className={data.setup_completed ? "badge-success" : "badge-warning"}>{data.setup_completed ? "Setup complete" : "Setup required"}</Badge></Card></div>}</>;
}

