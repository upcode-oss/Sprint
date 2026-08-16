"use client";

import { Mail, Save, Send } from "lucide-react";
import { FormEvent, useEffect, useState } from "react";

import { PageHeader } from "@/components/page-header";
import { Button } from "@/components/ui/button";
import { Card, CardHeader } from "@/components/ui/card";
import { Field, Input, Select } from "@/components/ui/form";
import { ErrorState, LoadingState } from "@/components/ui/states";
import { useToast } from "@/components/ui/toast";
import { useResource } from "@/hooks/use-resource";
import { api, jsonBody } from "@/services/api";
import type { Timestamped } from "@/types/api";

type Smtp = Timestamped & { host: string; port: number; username: string | null; encryption: string; from_address: string; from_name: string; is_enabled: boolean; has_password: boolean };
const empty = { host: "", port: 587, username: "", password: "", encryption: "starttls", from_address: "", from_name: "", is_enabled: true };
export default function SmtpPage() {
  const resource = useResource<Smtp | null>("/settings/smtp"); const { notify } = useToast(); const [form, setForm] = useState(empty); const [recipient, setRecipient] = useState(""); const [saving, setSaving] = useState(false);
  useEffect(() => { if (resource.data) setForm({ host: resource.data.host, port: resource.data.port, username: resource.data.username ?? "", password: "", encryption: resource.data.encryption, from_address: resource.data.from_address, from_name: resource.data.from_name, is_enabled: resource.data.is_enabled }); }, [resource.data]);
  async function save(event: FormEvent) { event.preventDefault(); setSaving(true); try { await api("/settings/smtp", { method: "PUT", body: jsonBody({ ...form, password: form.password || null }) }); notify("SMTP configuration saved"); setForm((value) => ({ ...value, password: "" })); await resource.reload(); } catch (reason) { notify((reason as Error).message, "error"); } finally { setSaving(false); } }
  async function test() { setSaving(true); try { await api(`/settings/smtp/test?recipient=${encodeURIComponent(recipient)}`, { method: "POST" }); notify("Test email sent"); } catch (reason) { notify((reason as Error).message, "error"); } finally { setSaving(false); } }
  return <><PageHeader title="SMTP" description="Credentials are encrypted at rest and are never returned by the API." />{resource.loading ? <LoadingState /> : resource.error ? <ErrorState message={resource.error} retry={resource.reload} /> : <div className="content-grid"><Card><CardHeader title="Mail server" action={<Mail />} /><form className="form-grid" onSubmit={save}><label className="user-chip"><input type="checkbox" checked={form.is_enabled} onChange={(event) => setForm({ ...form, is_enabled: event.target.checked })} />Enable email delivery</label><div className="form-grid two"><Field label="Host"><Input required value={form.host} onChange={(event) => setForm({ ...form, host: event.target.value })} /></Field><Field label="Port"><Input required type="number" min={1} max={65535} value={form.port} onChange={(event) => setForm({ ...form, port: Number(event.target.value) })} /></Field><Field label="Username"><Input autoComplete="username" value={form.username} onChange={(event) => setForm({ ...form, username: event.target.value })} /></Field><Field label="Password" hint={resource.data?.has_password ? "Leave blank to keep the stored password." : undefined}><Input type="password" autoComplete="new-password" value={form.password} onChange={(event) => setForm({ ...form, password: event.target.value })} /></Field><Field label="Encryption"><Select value={form.encryption} onChange={(event) => setForm({ ...form, encryption: event.target.value })}><option value="none">None</option><option value="starttls">STARTTLS</option><option value="tls">TLS</option></Select></Field><Field label="From address"><Input required type="email" value={form.from_address} onChange={(event) => setForm({ ...form, from_address: event.target.value })} /></Field></div><Field label="From name"><Input required value={form.from_name} onChange={(event) => setForm({ ...form, from_name: event.target.value })} /></Field><div className="form-actions"><Button loading={saving}><Save />Save SMTP</Button></div></form></Card><Card><CardHeader title="Connection test" description="Save the configuration before testing it." action={<Send />} /><div className="form-grid"><Field label="Recipient"><Input required type="email" value={recipient} onChange={(event) => setRecipient(event.target.value)} /></Field><Button variant="outline" disabled={!recipient || !resource.data} loading={saving} onClick={test}><Send />Send test email</Button></div></Card></div>}</>;
}

