"use client";

import { Building2, Save } from "lucide-react";
import { FormEvent, useEffect, useState } from "react";

import { PageHeader } from "@/components/page-header";
import { Button } from "@/components/ui/button";
import { Card, CardHeader } from "@/components/ui/card";
import { Field, Input } from "@/components/ui/form";
import { ErrorState, LoadingState } from "@/components/ui/states";
import { useToast } from "@/components/ui/toast";
import { useResource } from "@/hooks/use-resource";
import { api, jsonBody } from "@/services/api";
import type { Timestamped } from "@/types/api";

type Organization = Timestamped & { name: string };
export default function OrganizationPage() {
  const resource = useResource<Organization>("/organization"); const { notify } = useToast(); const [name, setName] = useState(""); const [saving, setSaving] = useState(false); useEffect(() => { if (resource.data) setName(resource.data.name); }, [resource.data]);
  async function save(event: FormEvent) { event.preventDefault(); setSaving(true); try { await api("/organization", { method: "PATCH", body: jsonBody({ name }) }); notify("Organization updated"); await resource.reload(); } catch (reason) { notify((reason as Error).message, "error"); } finally { setSaving(false); } }
  return <><PageHeader title="Organization" description="This installation represents exactly one organization." />{resource.loading ? <LoadingState /> : resource.error ? <ErrorState message={resource.error} retry={resource.reload} /> : <Card><CardHeader title="Organization identity" action={<Building2 />} /><form className="form-grid" onSubmit={save}><Field label="Name"><Input required minLength={2} maxLength={200} value={name} onChange={(event) => setName(event.target.value)} /></Field><Field label="Internal ID" hint="Stable UUID reserved for future multi-organization architecture."><Input disabled className="mono" value={resource.data?.id ?? ""} /></Field><div className="form-actions"><Button loading={saving}><Save />Save</Button></div></form></Card>}</>;
}

