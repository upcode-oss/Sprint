"use client";

import { Anchor, Check, ChevronLeft, ChevronRight, Database, Mail, ShieldCheck } from "lucide-react";
import Image from "next/image";
import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Field, Input, Select } from "@/components/ui/form";
import { useToast } from "@/components/ui/toast";
import { OrganizationBrandMark } from "@/components/organization-brand-mark";
import { ApiError, api, jsonBody } from "@/services/api";

type DatabaseEngine = "sqlite" | "postgresql" | "mysql" | "mariadb";
type SetupData = {
  organization_name: string;
  organization_logo_token: string;
  database: {
    engine: DatabaseEngine;
    sqlite_path: string;
    host: string;
    port: number;
    database: string;
    username: string;
    password: string;
    ssl: boolean;
  };
  admin: { username: string; email: string; password: string; first_name: string; last_name: string };
  smtp: {
    enabled: boolean;
    host: string;
    port: number;
    username: string;
    password: string;
    encryption: "none" | "starttls" | "tls";
    from_address: string;
    from_name: string;
  };
};

const initial: SetupData = {
  organization_name: "",
  organization_logo_token: "",
  database: { engine: "sqlite", sqlite_path: "/data/sprint.db", host: "", port: 5432, database: "", username: "", password: "", ssl: false },
  admin: { username: "", email: "", password: "", first_name: "", last_name: "" },
  smtp: { enabled: false, host: "", port: 587, username: "", password: "", encryption: "starttls", from_address: "", from_name: "" },
};

const steps = ["Organization", "Database", "Administrator", "Email"];

export function SetupWizard() {
  const router = useRouter();
  const { notify } = useToast();
  const [step, setStep] = useState(0);
  const [data, setData] = useState(initial);
  const [databaseTested, setDatabaseTested] = useState(false);
  const [loading, setLoading] = useState(false);
  const [logoPreview, setLogoPreview] = useState<string>();
  const [error, setError] = useState<string>();

  useEffect(() => {
    api<{ completed: boolean }>("/setup/status").then((value) => {
      if (value.completed) router.replace("/login");
    }).catch(() => undefined);
  }, [router]);

  function databasePayload() {
    return data.database.engine === "sqlite"
      ? { engine: "sqlite", sqlite_path: data.database.sqlite_path }
      : {
          engine: data.database.engine,
          host: data.database.host,
          port: data.database.port,
          database: data.database.database,
          username: data.database.username,
          password: data.database.password,
          ssl: data.database.ssl,
        };
  }

  async function testDatabase() {
    setLoading(true); setError(undefined);
    try {
      await api("/setup/database/test", { method: "POST", body: jsonBody(databasePayload()) });
      setDatabaseTested(true); notify("Database connection succeeded");
    } catch (reason) {
      setDatabaseTested(false); setError((reason as Error).message);
    } finally { setLoading(false); }
  }

  async function uploadLogo(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    const body = new FormData();
    body.set("logo", file);
    setLoading(true); setError(undefined);
    try {
      const result = await api<{ upload_token: string; preview_url: string }>("/setup/logo", { method: "POST", body });
      setData((current) => ({ ...current, organization_logo_token: result.upload_token }));
      setLogoPreview(result.preview_url);
      notify("Organization logo uploaded");
    } catch (reason) {
      setError((reason as Error).message);
    } finally {
      setLoading(false); event.target.value = "";
    }
  }

  async function testSmtp() {
    setLoading(true); setError(undefined);
    try {
      await api("/setup/smtp/test", { method: "POST", body: jsonBody({ smtp: data.smtp, recipient: data.admin.email }) });
      notify("Test email sent");
    } catch (reason) { setError((reason as Error).message); }
    finally { setLoading(false); }
  }

  async function finish(event: FormEvent) {
    event.preventDefault(); setLoading(true); setError(undefined);
    try {
      await api("/setup/complete", {
        method: "POST",
        body: jsonBody({
          organization_name: data.organization_name,
          organization_logo_token: data.organization_logo_token || null,
          database: databasePayload(),
          admin: data.admin,
          smtp: data.smtp.enabled ? data.smtp : { enabled: false },
        }),
      });
      notify("Setup completed. Sign in with your administrator account.");
      router.replace("/login");
    } catch (reason) {
      const apiError = reason as ApiError;
      setError(apiError.message);
    } finally { setLoading(false); }
  }

  const canContinue = step === 0 ? data.organization_name.trim().length >= 2 : step === 1 ? databaseTested : step === 2 ? Boolean(data.admin.username && data.admin.email && data.admin.first_name && data.admin.last_name && data.admin.password.length >= 12) : true;

  return (
    <div className="setup-shell">
      <div className="auth-heading">
        <OrganizationBrandMark className="auth-brand-mark" />
        <h1>Set up Upcode sprint</h1>
        <p>Configure the organization before the workspace becomes available.</p>
      </div>
      <div className="setup-progress" aria-label={`Step ${step + 1} of ${steps.length}`}>
        {steps.map((label, index) => <div key={label} className={`setup-step ${index === step ? "active" : ""} ${index < step ? "done" : ""}`}>{index < step ? <Check /> : index + 1} <span>{label}</span></div>)}
      </div>
      <Card className="setup-card">
        <form onSubmit={finish} className="form-grid">
          {step === 0 ? <>
            <div className="card-header"><div><h2>Organization</h2><p>One installation represents one organization.</p></div><Anchor /></div>
            <Field label="Organization name"><Input autoFocus required minLength={2} maxLength={200} value={data.organization_name} onChange={(event) => setData({ ...data, organization_name: event.target.value })} /></Field>
            <Field label="Organization logo" hint="Optional · the Sprint logo is used by default · JPEG, PNG or WebP.">
              <label className="organization-logo-upload">
                <span className="organization-logo-preview">
                  {logoPreview ? <Image src={logoPreview} alt="Organization logo preview" width={72} height={72} unoptimized /> : <Image src="/logo.png" alt="Default Sprint logo" width={72} height={72} />}
                </span>
                <span><strong>{logoPreview ? "Replace logo" : "Upload custom logo"}</strong><small>The original filename is never used for storage.</small></span>
                <input className="sr-only" type="file" accept="image/jpeg,image/png,image/webp" onChange={uploadLogo} disabled={loading} />
              </label>
            </Field>
          </> : null}
          {step === 1 ? <>
            <div className="card-header"><div><h2>Database</h2><p>Credentials are encrypted and never returned by the API.</p></div><Database /></div>
            <Field label="Database engine"><Select value={data.database.engine} onChange={(event) => { const engine = event.target.value as DatabaseEngine; setData({ ...data, database: { ...data.database, engine, port: engine === "postgresql" ? 5432 : engine === "sqlite" ? 0 : 3306 } }); setDatabaseTested(false); }}><option value="sqlite">SQLite</option><option value="postgresql">PostgreSQL</option><option value="mysql">MySQL</option><option value="mariadb">MariaDB</option></Select></Field>
            {data.database.engine === "sqlite" ? <Field label="Database file" hint="Use an absolute path inside the backend container."><Input required value={data.database.sqlite_path} onChange={(event) => { setData({ ...data, database: { ...data.database, sqlite_path: event.target.value } }); setDatabaseTested(false); }} /></Field> : <div className="form-grid two">
              <Field label="Host"><Input required value={data.database.host} onChange={(event) => { setData({ ...data, database: { ...data.database, host: event.target.value } }); setDatabaseTested(false); }} /></Field>
              <Field label="Port"><Input required type="number" min={1} max={65535} value={data.database.port} onChange={(event) => { setData({ ...data, database: { ...data.database, port: Number(event.target.value) } }); setDatabaseTested(false); }} /></Field>
              <Field label="Database"><Input required value={data.database.database} onChange={(event) => { setData({ ...data, database: { ...data.database, database: event.target.value } }); setDatabaseTested(false); }} /></Field>
              <Field label="Username"><Input required autoComplete="username" value={data.database.username} onChange={(event) => { setData({ ...data, database: { ...data.database, username: event.target.value } }); setDatabaseTested(false); }} /></Field>
              <Field label="Password"><Input required type="password" autoComplete="new-password" value={data.database.password} onChange={(event) => { setData({ ...data, database: { ...data.database, password: event.target.value } }); setDatabaseTested(false); }} /></Field>
              <Field label="Transport security"><label className="user-chip"><input type="checkbox" checked={data.database.ssl} onChange={(event) => { setData({ ...data, database: { ...data.database, ssl: event.target.checked } }); setDatabaseTested(false); }} /> Require SSL</label></Field>
            </div>}
            <div><Button type="button" variant="outline" loading={loading} onClick={testDatabase}><Database />{databaseTested ? "Connection verified" : "Test connection"}</Button></div>
          </> : null}
          {step === 2 ? <>
            <div className="card-header"><div><h2>Administrator</h2><p>This account receives the protected Admin system role.</p></div><ShieldCheck /></div>
            <div className="form-grid two">
              <Field label="First name"><Input autoFocus required value={data.admin.first_name} onChange={(event) => setData({ ...data, admin: { ...data.admin, first_name: event.target.value } })} /></Field>
              <Field label="Last name"><Input required value={data.admin.last_name} onChange={(event) => setData({ ...data, admin: { ...data.admin, last_name: event.target.value } })} /></Field>
              <Field label="Username"><Input required minLength={3} autoComplete="username" value={data.admin.username} onChange={(event) => setData({ ...data, admin: { ...data.admin, username: event.target.value } })} /></Field>
              <Field label="Email"><Input required type="email" value={data.admin.email} onChange={(event) => setData({ ...data, admin: { ...data.admin, email: event.target.value } })} /></Field>
            </div>
            <Field label="Password" hint="At least 12 characters with uppercase, lowercase and a number."><Input required minLength={12} type="password" autoComplete="new-password" value={data.admin.password} onChange={(event) => setData({ ...data, admin: { ...data.admin, password: event.target.value } })} /></Field>
          </> : null}
          {step === 3 ? <>
            <div className="card-header"><div><h2>Email delivery</h2><p>SMTP is optional and can be configured later.</p></div><Mail /></div>
            <label className="user-chip"><input type="checkbox" checked={data.smtp.enabled} onChange={(event) => setData({ ...data, smtp: { ...data.smtp, enabled: event.target.checked } })} /> Enable SMTP</label>
            {data.smtp.enabled ? <>
              <div className="form-grid two">
                <Field label="SMTP host"><Input required value={data.smtp.host} onChange={(event) => setData({ ...data, smtp: { ...data.smtp, host: event.target.value } })} /></Field>
                <Field label="Port"><Input required type="number" min={1} max={65535} value={data.smtp.port} onChange={(event) => setData({ ...data, smtp: { ...data.smtp, port: Number(event.target.value) } })} /></Field>
                <Field label="Username"><Input autoComplete="username" value={data.smtp.username} onChange={(event) => setData({ ...data, smtp: { ...data.smtp, username: event.target.value } })} /></Field>
                <Field label="Password"><Input type="password" autoComplete="new-password" value={data.smtp.password} onChange={(event) => setData({ ...data, smtp: { ...data.smtp, password: event.target.value } })} /></Field>
                <Field label="Encryption"><Select value={data.smtp.encryption} onChange={(event) => setData({ ...data, smtp: { ...data.smtp, encryption: event.target.value as SetupData["smtp"]["encryption"] } })}><option value="none">None</option><option value="starttls">STARTTLS</option><option value="tls">TLS</option></Select></Field>
                <Field label="From address"><Input required type="email" value={data.smtp.from_address} onChange={(event) => setData({ ...data, smtp: { ...data.smtp, from_address: event.target.value } })} /></Field>
                <Field label="From name"><Input required value={data.smtp.from_name} onChange={(event) => setData({ ...data, smtp: { ...data.smtp, from_name: event.target.value } })} /></Field>
              </div>
              <div><Button type="button" variant="outline" loading={loading} onClick={testSmtp}><Mail />Send test email</Button></div>
            </> : null}
          </> : null}
          {error ? <p className="field-error" role="alert">{error}</p> : null}
          <div className="form-actions">
            {step > 0 ? <Button type="button" variant="outline" onClick={() => { setError(undefined); setStep(step - 1); }}><ChevronLeft />Back</Button> : null}
            {step < steps.length - 1 ? <Button type="button" disabled={!canContinue} onClick={() => { setError(undefined); setStep(step + 1); }}>Continue<ChevronRight /></Button> : <Button type="submit" loading={loading}>Complete setup<Check /></Button>}
          </div>
        </form>
      </Card>
    </div>
  );
}
