"use client";

import { Building2, Save, Upload } from "lucide-react";
import Image from "next/image";
import { ChangeEvent, FormEvent, useEffect, useState } from "react";

import { PageHeader } from "@/components/page-header";
import { Button } from "@/components/ui/button";
import { Card, CardHeader } from "@/components/ui/card";
import { Field, Input } from "@/components/ui/form";
import { ErrorState, LoadingState } from "@/components/ui/states";
import { useToast } from "@/components/ui/toast";
import { useResource } from "@/hooks/use-resource";
import { api, jsonBody } from "@/services/api";
import type { Timestamped } from "@/types/api";

type Organization = Timestamped & { name: string; logo_url: string | null };
export default function OrganizationPage() {
  const resource = useResource<Organization>("/organization"); const { notify } = useToast(); const [name, setName] = useState(""); const [saving, setSaving] = useState(false); useEffect(() => { if (resource.data) setName(resource.data.name); }, [resource.data]);
  function announceBrandingUpdate() { window.dispatchEvent(new Event("organization-branding-updated")); }
  async function save(event: FormEvent) { event.preventDefault(); setSaving(true); try { await api("/organization", { method: "PATCH", body: jsonBody({ name }) }); notify("Organization updated"); await resource.reload(); announceBrandingUpdate(); } catch (reason) { notify((reason as Error).message, "error"); } finally { setSaving(false); } }
  async function uploadLogo(event: ChangeEvent<HTMLInputElement>) { const file = event.target.files?.[0]; if (!file) return; const body = new FormData(); body.set("logo", file); setSaving(true); try { await api("/organization/logo", { method: "POST", body }); notify("Organization logo updated"); await resource.reload(); announceBrandingUpdate(); } catch (reason) { notify((reason as Error).message, "error"); } finally { setSaving(false); event.target.value = ""; } }
  return <><PageHeader title="Organization" description="This installation represents exactly one organization." />{resource.loading ? <LoadingState /> : resource.error ? <ErrorState message={resource.error} retry={resource.reload} /> : <Card><CardHeader title="Organization identity" action={<Building2 />} /><form className="form-grid" onSubmit={save}><div className="organization-settings-logo">{resource.data?.logo_url ? <Image src={resource.data.logo_url} alt={`${resource.data.name} logo`} width={72} height={72} unoptimized /> : <Building2 />}<div><strong>Organization logo</strong><p className="muted small">JPEG, PNG or WebP · stored with a random internal filename.</p><label className="button button-outline button-default"><Upload />Replace logo<input className="sr-only" type="file" accept="image/jpeg,image/png,image/webp" onChange={uploadLogo} disabled={saving} /></label></div></div><Field label="Name"><Input required minLength={2} maxLength={200} value={name} onChange={(event) => setName(event.target.value)} /></Field><Field label="Internal ID" hint="Stable UUID reserved for future multi-organization architecture."><Input disabled className="mono" value={resource.data?.id ?? ""} /></Field><div className="form-actions"><Button loading={saving}><Save />Save</Button></div></form></Card>}</>;
}
