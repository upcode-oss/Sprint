"use client";

import { Anchor, LogIn } from "lucide-react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { FormEvent, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Field, Input } from "@/components/ui/form";
import { api, jsonBody } from "@/services/api";

export function LoginForm() {
  const router = useRouter();
  const search = useSearchParams();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string>();
  async function submit(event: FormEvent) {
    event.preventDefault(); setLoading(true); setError(undefined);
    try {
      await api("/auth/login", { method: "POST", body: jsonBody({ username, password }) });
      const next = search.get("next");
      router.replace(next?.startsWith("/") && !next.startsWith("//") ? next : "/dashboard");
      router.refresh();
    } catch (reason) { setError((reason as Error).message); }
    finally { setLoading(false); }
  }
  return <Card className="auth-card">
    <div className="auth-heading"><div className="brand-mark"><Anchor /></div><h1>Welcome back</h1><p>Sign in to your organization workspace.</p></div>
    <form className="form-grid" onSubmit={submit}>
      <Field label="Username or email"><Input autoFocus required autoComplete="username" value={username} onChange={(event) => setUsername(event.target.value)} /></Field>
      <Field label="Password"><Input required type="password" autoComplete="current-password" value={password} onChange={(event) => setPassword(event.target.value)} /></Field>
      {error ? <p className="field-error" role="alert">{error}</p> : null}
      <Button type="submit" loading={loading}><LogIn />Sign in</Button>
    </form>
    <div className="auth-links"><Link href="/forgot-password">Forgot password?</Link></div>
  </Card>;
}

