"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Field, Input } from "@/components/ui/form";
import { LoadingState } from "@/components/ui/states";
import { ApiError, api, jsonBody } from "@/services/api";

type ConsentDetails = {
  client_name: string;
  redirect_uri: string;
  username: string;
  csrf_token: string;
  requires_two_factor: boolean;
  expires_in_days: number;
  permissions: { scope: string; description: string }[];
};

export function OAuthConsent() {
  const requestId = useSearchParams().get("request");
  const router = useRouter();
  const [details, setDetails] = useState<ConsentDetails>();
  const [scopes, setScopes] = useState<string[]>([]);
  const [password, setPassword] = useState("");
  const [code, setCode] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string>();
  const next = `/oauth/authorize?request=${encodeURIComponent(requestId ?? "")}`;

  useEffect(() => {
    if (!requestId) return;
    let active = true;
    api<ConsentDetails>(`/oauth/consent/${encodeURIComponent(requestId)}`)
      .then((value) => {
        if (!active) return;
        setDetails(value);
        setScopes(
          value.permissions
            .filter(({ scope }) => scope.endsWith(".read") || scope.endsWith(".view"))
            .map(({ scope }) => scope),
        );
      })
      .catch((reason: unknown) => {
        if (!active) return;
        if (reason instanceof ApiError && reason.status === 401) {
          router.replace(`/login?next=${encodeURIComponent(next)}`);
        } else {
          setError(
            reason instanceof Error ? reason.message : "Could not load the connection request.",
          );
        }
      });
    return () => {
      active = false;
    };
  }, [requestId, router, next]);

  async function decide(approved: boolean) {
    if (!details || busy) return;
    setBusy(true);
    setError(undefined);
    try {
      const result = await api<{ redirect_uri: string }>(
        `/oauth/consent/${encodeURIComponent(requestId ?? "")}`,
        {
          method: "POST",
          body: jsonBody({
            approved,
            csrf_token: details.csrf_token,
            ...(approved ? { scopes, password, ...(code ? { two_factor_code: code } : {}) } : {}),
          }),
        },
        false,
      );
      setPassword("");
      setCode("");
      window.location.assign(result.redirect_uri);
    } catch (reason) {
      setError(
        reason instanceof Error ? reason.message : "The connection could not be authorized.",
      );
      setBusy(false);
    }
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void decide(true);
  }

  if (!requestId)
    return (
      <Card className="auth-card">
        <p>Start the connection from your MCP client.</p>
      </Card>
    );
  if (!details)
    return (
      <Card className="auth-card">
        {error ? (
          <p className="field-error" role="alert">
            {error}
          </p>
        ) : (
          <LoadingState label="Loading connection request…" />
        )}
      </Card>
    );

  return (
    <Card className="auth-card">
      <div className="auth-heading">
        <h1>Connect your Sprint account</h1>
        <p>
          <strong>{details.client_name}</strong> is requesting access as{" "}
          <strong>{details.username}</strong>.
        </p>
      </div>
      <p className="muted">Check the application&apos;s callback address before approving:</p>
      <p style={{ overflowWrap: "anywhere" }}>{details.redirect_uri}</p>
      <form className="form-grid" onSubmit={submit}>
        <fieldset className="form-grid" disabled={busy}>
          <legend>Choose permissions</legend>
          <div className="form-grid" style={{ maxHeight: "18rem", overflowY: "auto" }}>
            {details.permissions.map(({ scope, description }) => (
              <label className="user-chip" key={scope}>
                <input
                  type="checkbox"
                  checked={scopes.includes(scope)}
                  onChange={(event) =>
                    setScopes((current) =>
                      event.target.checked
                        ? [...current, scope]
                        : current.filter((value) => value !== scope),
                    )
                  }
                />
                {description}
              </label>
            ))}
          </div>
        </fieldset>
        <p className="muted">
          Access expires after {details.expires_in_days} days. You can revoke it at any time under
          Profile → MCP access keys.
        </p>
        <Field label="Confirm your Sprint password">
          <Input
            required
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            disabled={busy}
          />
        </Field>
        {details.requires_two_factor ? (
          <Field label="Authenticator or recovery code">
            <Input
              required
              autoComplete="one-time-code"
              maxLength={32}
              value={code}
              onChange={(event) => setCode(event.target.value)}
              disabled={busy}
            />
          </Field>
        ) : null}
        {error ? (
          <p className="field-error" role="alert">
            {error}
          </p>
        ) : null}
        <div className="form-actions">
          <Button
            type="button"
            variant="outline"
            disabled={busy}
            onClick={() => void decide(false)}
          >
            Deny
          </Button>
          <Button type="submit" loading={busy} disabled={scopes.length === 0}>
            Allow access
          </Button>
        </div>
      </form>
      <div className="auth-links">
        <Link href={`/login?next=${encodeURIComponent(next)}`}>Use another account</Link>
      </div>
    </Card>
  );
}
