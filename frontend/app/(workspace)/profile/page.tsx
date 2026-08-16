"use client";

import { KeyRound, Save, UserRound } from "lucide-react";
import { FormEvent, useState } from "react";

import { PageHeader } from "@/components/page-header";
import { Button } from "@/components/ui/button";
import { Card, CardHeader } from "@/components/ui/card";
import { Field, Input } from "@/components/ui/form";
import { useToast } from "@/components/ui/toast";
import { useAuth } from "@/features/auth/auth-context";
import { api, jsonBody } from "@/services/api";

export default function ProfilePage() {
  const { user, reload } = useAuth(); const { notify } = useToast(); const [saving, setSaving] = useState(false); const [profile, setProfile] = useState({ first_name: user.first_name, last_name: user.last_name, email: user.email }); const [passwords, setPasswords] = useState({ current_password: "", password: "" });
  async function saveProfile(event: FormEvent) { event.preventDefault(); setSaving(true); try { await api("/auth/me", { method: "PATCH", body: jsonBody(profile) }); await reload(); notify("Profile updated"); } catch (reason) { notify((reason as Error).message, "error"); } finally { setSaving(false); } }
  async function savePassword(event: FormEvent) { event.preventDefault(); setSaving(true); try { await api("/auth/change-password", { method: "POST", body: jsonBody(passwords) }); setPasswords({ current_password: "", password: "" }); notify("Password changed"); } catch (reason) { notify((reason as Error).message, "error"); } finally { setSaving(false); } }
  return <><PageHeader title="Profile" description={`Signed in as @${user.username}`} /><div className="content-grid"><Card><CardHeader title="Personal information" action={<UserRound />} /><form className="form-grid" onSubmit={saveProfile}><div className="form-grid two"><Field label="First name"><Input required value={profile.first_name} onChange={(event) => setProfile({ ...profile, first_name: event.target.value })} /></Field><Field label="Last name"><Input required value={profile.last_name} onChange={(event) => setProfile({ ...profile, last_name: event.target.value })} /></Field></div><Field label="Email"><Input required type="email" value={profile.email} onChange={(event) => setProfile({ ...profile, email: event.target.value })} /></Field><div className="form-actions"><Button loading={saving}><Save />Save profile</Button></div></form></Card><Card><CardHeader title="Change password" description="Changing the password revokes other sessions." action={<KeyRound />} /><form className="form-grid" onSubmit={savePassword}><Field label="Current password"><Input required type="password" autoComplete="current-password" value={passwords.current_password} onChange={(event) => setPasswords({ ...passwords, current_password: event.target.value })} /></Field><Field label="New password" hint="At least 12 characters with upper, lower and numeric characters."><Input required minLength={12} type="password" autoComplete="new-password" value={passwords.password} onChange={(event) => setPasswords({ ...passwords, password: event.target.value })} /></Field><div className="form-actions"><Button loading={saving}><KeyRound />Change password</Button></div></form></Card></div></>;
}

