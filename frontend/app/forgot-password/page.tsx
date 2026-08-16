"use client";

import { Mail } from "lucide-react";
import Link from "next/link";
import { FormEvent, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Field, Input } from "@/components/ui/form";
import { api, jsonBody } from "@/services/api";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState(""); const [message, setMessage] = useState<string>(); const [loading, setLoading] = useState(false);
  async function submit(event: FormEvent) { event.preventDefault(); setLoading(true); try { const response = await api<{ message: string }>("/auth/forgot-password", { method: "POST", body: jsonBody({ email }) }); setMessage(response.message); } catch (reason) { setMessage((reason as Error).message); } finally { setLoading(false); } }
  return <main className="centered-page"><Card className="auth-card"><div className="auth-heading"><div className="brand-mark"><Mail /></div><h1>Reset password</h1><p>We will send a reset link when SMTP is available.</p></div><form className="form-grid" onSubmit={submit}><Field label="Email"><Input required type="email" value={email} onChange={(event) => setEmail(event.target.value)} /></Field>{message ? <p className="muted" role="status">{message}</p> : null}<Button loading={loading}>Send reset link</Button></form><div className="auth-links"><Link href="/login">Back to sign in</Link></div></Card></main>;
}

