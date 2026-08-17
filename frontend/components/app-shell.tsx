"use client";

import {
  Anchor,
  BarChart3,
  CalendarDays,
  FolderKanban,
  LogOut,
  Menu,
  MessagesSquare,
  Moon,
  Settings,
  Shield,
  Sun,
  UserRound,
  Users,
  X,
} from "lucide-react";
import { useTheme } from "next-themes";
import Image from "next/image";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { UserAvatar } from "@/components/user-avatar";
import { useAuth } from "@/features/auth/auth-context";
import { useResource } from "@/hooks/use-resource";
import { api } from "@/services/api";

type NavItem = { label: string; href: string; icon: typeof BarChart3; permission?: string };
type OrganizationBranding = { name: string; logo_url: string | null; version: string };
const workspace: NavItem[] = [
  { label: "Dashboard", href: "/dashboard", icon: BarChart3 },
  { label: "Projects", href: "/projects", icon: FolderKanban, permission: "projects.view" },
  { label: "Teams", href: "/teams", icon: Users, permission: "teams.view" },
  { label: "Calendar", href: "/calendar", icon: CalendarDays, permission: "calendar.view" },
  { label: "Meetings", href: "/meetings", icon: MessagesSquare, permission: "meetings.view" },
];
const administration: NavItem[] = [
  { label: "Users", href: "/users", icon: Users, permission: "users.view" },
  { label: "Roles", href: "/administration/roles", icon: Shield, permission: "roles.view" },
  { label: "Organization", href: "/administration/organization", icon: Settings, permission: "organization.manage" },
  { label: "SMTP", href: "/administration/smtp", icon: Settings, permission: "settings.manage" },
  { label: "System", href: "/administration/system", icon: Settings, permission: "settings.manage" },
];

function NavigationItem({ item, close }: { item: NavItem; close: () => void }) {
  const pathname = usePathname(); const active = pathname === item.href || (item.href !== "/dashboard" && pathname.startsWith(`${item.href}/`)); const Icon = item.icon;
  return <Link href={item.href} onClick={close} className={`nav-item ${active ? "active" : ""}`}><Icon />{item.label}</Link>;
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const { user, hasPermission } = useAuth(); const router = useRouter(); const { resolvedTheme, setTheme } = useTheme(); const [mounted, setMounted] = useState(false); const [open, setOpen] = useState(false);
  const { data: branding, reload: reloadBranding } = useResource<OrganizationBranding>("/organization/branding");
  useEffect(() => setMounted(true), []);
  useEffect(() => {
    const reload = () => void reloadBranding();
    window.addEventListener("organization-branding-updated", reload);
    return () => window.removeEventListener("organization-branding-updated", reload);
  }, [reloadBranding]);
  const visibleAdmin = administration.filter((item) => !item.permission || hasPermission(item.permission));
  async function logout() { await api("/auth/logout", { method: "POST" }).catch(() => undefined); router.replace("/login"); router.refresh(); }
  const isDark = mounted && resolvedTheme === "dark";
  return <div className="app-layout">
    {open ? <div className="sidebar-scrim" onClick={() => setOpen(false)} aria-hidden /> : null}
    <aside className={`sidebar upcode-sprint-sidebar ${open ? "open" : ""}`}>
      <div className="sidebar-brand"><div className={branding?.logo_url ? "organization-brand-mark" : "brand-mark"}>{branding?.logo_url ? <Image src={branding.logo_url} alt={`${branding.name} logo`} width={40} height={40} unoptimized /> : <Anchor />}</div><div className="sidebar-brand-copy"><strong>{branding?.name ?? "Upcode sprint"}</strong><span className="mono">Version {branding?.version ?? "0.1.0"}</span></div><Button className="mobile-menu" style={{ marginLeft: "auto" }} variant="ghost" size="icon" onClick={() => setOpen(false)} aria-label="Close navigation"><X /></Button></div>
      <nav className="sidebar-nav" aria-label="Primary navigation">
        <div className="nav-category">Workspace</div>
        {workspace.filter((item) => !item.permission || hasPermission(item.permission)).map((item) => <NavigationItem key={item.href} item={item} close={() => setOpen(false)} />)}
        {visibleAdmin.length ? <><div className="nav-category">Administration</div>{visibleAdmin.map((item) => <NavigationItem key={item.href} item={item} close={() => setOpen(false)} />)}</> : null}
        <div className="nav-category">Account</div><NavigationItem item={{ label: "Profile", href: "/profile", icon: UserRound }} close={() => setOpen(false)} />
      </nav>
      <div className="sidebar-footer">
        <button className="theme-switch" type="button" role="switch" aria-checked={isDark} aria-label={`Switch to ${isDark ? "light" : "dark"} mode`} data-theme={isDark ? "dark" : "light"} disabled={!mounted} onClick={() => setTheme(isDark ? "light" : "dark")}>
          <span className="theme-switch-thumb" aria-hidden />
          <span className={`theme-switch-option ${!isDark ? "active" : ""}`}><Sun />Light</span>
          <span className={`theme-switch-option ${isDark ? "active" : ""}`}><Moon />Dark</span>
        </button>
        <div className="split"><Link href="/profile" className="user-chip"><UserAvatar user={user} /><div><strong>{user.display_name}</strong><span>{user.presence.status_message || `@${user.username}`}</span></div></Link><Button variant="ghost" size="icon" onClick={logout} aria-label="Log out"><LogOut /></Button></div>
      </div>
    </aside>
    <div className="app-content">
      <main className="main-content"><div className="page-container"><Button className="mobile-menu mobile-navigation-trigger" variant="outline" size="icon" onClick={() => setOpen(true)} aria-label="Open navigation"><Menu /></Button>{children}</div></main>
    </div>
  </div>;
}
