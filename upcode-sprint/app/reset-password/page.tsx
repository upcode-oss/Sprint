"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { FormEvent, Suspense, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Field, Input } from "@/components/ui/form";
import { OrganizationBrandMark } from "@/components/organization-brand-mark";
import { api, jsonBody } from "@/services/api";

function ResetForm() {
  const token = useSearchParams().get("token") ?? ""; const [password, setPassword] = useState(""); const [message, setMessage] = useState<string>(); const [loading, setLoading] = useState(false);
  async function submit(event: FormEvent) { event.preventDefault(); setLoading(true); try { const response = await api<{ message: string }>("/auth/reset-password", { method: "POST", body: jsonBody({ token, password }) }); setMessage(response.message); } catch (reason) { setMessage((reason as Error).message); } finally { setLoading(false); } }
  return <Card className="auth-card"><div className="auth-heading"><OrganizationBrandMark className="auth-brand-mark" /><h1>Choose a new password</h1><p>The link is valid for 30 minutes.</p></div><form className="form-grid" onSubmit={submit}><Field label="New password" hint="At least 12 characters with upper, lower and numeric characters."><Input required minLength={12} type="password" autoComplete="new-password" value={password} onChange={(event) => setPassword(event.target.value)} /></Field>{message ? <p className="muted">{message}</p> : null}<Button disabled={!token} loading={loading}>Reset password</Button></form><div className="auth-links"><Link href="/login">Back to sign in</Link></div></Card>;
}
export default function ResetPasswordPage() { return <main className="centered-page"><Suspense><ResetForm /></Suspense></main>; }
