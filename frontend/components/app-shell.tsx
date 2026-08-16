"use client";

import {
  Anchor,
  BarChart3,
  CalendarDays,
  ChevronRight,
  FolderKanban,
  LogOut,
  Menu,
  Moon,
  Settings,
  Shield,
  Sun,
  UserRound,
  Users,
  X,
} from "lucide-react";
import { useTheme } from "next-themes";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { useAuth } from "@/features/auth/auth-context";
import { initials } from "@/lib/utils";
import { api } from "@/services/api";

type NavItem = { label: string; href: string; icon: typeof BarChart3; permission?: string };
const workspace: NavItem[] = [
  { label: "Dashboard", href: "/dashboard", icon: BarChart3 },
  { label: "Projects", href: "/projects", icon: FolderKanban, permission: "projects.view" },
  { label: "Teams", href: "/teams", icon: Users, permission: "teams.view" },
  { label: "Calendar", href: "/calendar", icon: CalendarDays, permission: "calendar.view" },
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
  return <Link href={item.href} onClick={close} className={`nav-item ${active ? "active" : ""}`}><Icon />{item.label}{!active ? <ChevronRight style={{ marginLeft: "auto" }} /> : null}</Link>;
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const { user, hasPermission } = useAuth(); const router = useRouter(); const pathname = usePathname(); const { resolvedTheme, setTheme } = useTheme(); const [mounted, setMounted] = useState(false); const [open, setOpen] = useState(false);
  useEffect(() => setMounted(true), []);
  const visibleAdmin = administration.filter((item) => !item.permission || hasPermission(item.permission));
  const title = [...workspace, ...administration, { label: "Profile", href: "/profile", icon: UserRound }].find((item) => pathname === item.href || pathname.startsWith(`${item.href}/`))?.label ?? "Upcode Harbor";
  async function logout() { await api("/auth/logout", { method: "POST" }).catch(() => undefined); router.replace("/login"); router.refresh(); }
  return <div className="app-layout">
    {open ? <div className="sidebar-scrim" onClick={() => setOpen(false)} aria-hidden /> : null}
    <aside className={`sidebar upcode-harbor-sidebar ${open ? "open" : ""}`}>
      <div className="sidebar-brand"><div className="brand-mark"><Anchor /></div><div><strong>Upcode Harbor</strong><span>Organization workspace</span></div><Button className="mobile-menu" style={{ marginLeft: "auto" }} variant="ghost" size="icon" onClick={() => setOpen(false)} aria-label="Close navigation"><X /></Button></div>
      <nav className="sidebar-nav" aria-label="Primary navigation">
        <div className="nav-category">Workspace</div>
        {workspace.filter((item) => !item.permission || hasPermission(item.permission)).map((item) => <NavigationItem key={item.href} item={item} close={() => setOpen(false)} />)}
        {visibleAdmin.length ? <><div className="nav-category">Administration</div>{visibleAdmin.map((item) => <NavigationItem key={item.href} item={item} close={() => setOpen(false)} />)}</> : null}
        <div className="nav-category">Account</div><NavigationItem item={{ label: "Profile", href: "/profile", icon: UserRound }} close={() => setOpen(false)} />
      </nav>
      <div className="sidebar-footer"><div className="split"><Link href="/profile" className="user-chip"><span className="avatar">{initials(user.first_name, user.last_name)}</span><div><strong>{user.first_name} {user.last_name}</strong><span>@{user.username}</span></div></Link><Button variant="ghost" size="icon" onClick={logout} aria-label="Log out"><LogOut /></Button></div></div>
    </aside>
    <div className="app-content">
      <header className="topbar"><Button className="mobile-menu" variant="ghost" size="icon" onClick={() => setOpen(true)} aria-label="Open navigation"><Menu /></Button><div className="topbar-title"><strong>{title}</strong><span>Upcode Harbor</span></div>{mounted ? <Button variant="ghost" size="icon" onClick={() => setTheme(resolvedTheme === "dark" ? "light" : "dark")} aria-label="Toggle color theme">{resolvedTheme === "dark" ? <Sun /> : <Moon />}</Button> : null}</header>
      <main className="main-content"><div className="page-container">{children}</div></main>
    </div>
  </div>;
}

