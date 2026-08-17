"use client";

import {
  Anchor,
  BarChart3,
  CalendarDays,
  ChevronRight,
  FolderKanban,
  LogOut,
  Menu,
  MessagesSquare,
  Monitor,
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
import { useEffect, useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { UserAvatar } from "@/components/user-avatar";
import { useAuth } from "@/features/auth/auth-context";
import { useResource } from "@/hooks/use-resource";
import { api } from "@/services/api";

type NavItem = { label: string; href: string; icon: typeof BarChart3; permission?: string };
type OrganizationBranding = { name: string; logo_url: string | null; version: string };
type ThemeChoice = "light" | "system" | "dark";

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

const themeChoices: Array<{ value: ThemeChoice; label: string; icon: typeof Sun }> = [
  { value: "light", label: "Light", icon: Sun },
  { value: "system", label: "System", icon: Monitor },
  { value: "dark", label: "Dark", icon: Moon },
];

function NavigationItem({ item, close }: { item: NavItem; close: () => void }) {
  const pathname = usePathname();
  const active = pathname === item.href || (item.href !== "/dashboard" && pathname.startsWith(`${item.href}/`));
  const Icon = item.icon;

  return (
    <Link
      href={item.href}
      onClick={close}
      className={`nav-item ${active ? "active" : ""}`}
      aria-current={active ? "page" : undefined}
    >
      <Icon aria-hidden />
      <span>{item.label}</span>
      {!active ? <ChevronRight aria-hidden style={{ marginLeft: "auto" }} /> : null}
    </Link>
  );
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const { user, hasPermission } = useAuth();
  const router = useRouter();
  const pathname = usePathname();
  const { theme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);
  const [open, setOpen] = useState(false);
  const menuButtonRef = useRef<HTMLButtonElement>(null);
  const closeButtonRef = useRef<HTMLButtonElement>(null);
  const { data: branding, reload: reloadBranding } = useResource<OrganizationBranding>("/organization/branding");

  useEffect(() => setMounted(true), []);
  useEffect(() => setOpen(false), [pathname]);
  useEffect(() => {
    if (open) closeButtonRef.current?.focus();
  }, [open]);
  useEffect(() => {
    if (!open) return;
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setOpen(false);
        window.requestAnimationFrame(() => menuButtonRef.current?.focus());
      }
    };
    window.addEventListener("keydown", closeOnEscape);
    return () => window.removeEventListener("keydown", closeOnEscape);
  }, [open]);
  useEffect(() => {
    const reload = () => void reloadBranding();
    window.addEventListener("organization-branding-updated", reload);
    return () => window.removeEventListener("organization-branding-updated", reload);
  }, [reloadBranding]);

  const visibleAdmin = administration.filter((item) => !item.permission || hasPermission(item.permission));
  const title = [...workspace, ...administration, { label: "Profile", href: "/profile", icon: UserRound }]
    .find((item) => pathname === item.href || pathname.startsWith(`${item.href}/`))?.label ?? "Upcode sprint";

  async function logout() {
    await api("/auth/logout", { method: "POST" }).catch(() => undefined);
    router.replace("/login");
    router.refresh();
  }

  return (
    <div className="app-layout">
      <a className="skip-link" href="#main-content">Skip to main content</a>
      {open ? <button className="sidebar-scrim" type="button" onClick={() => { setOpen(false); menuButtonRef.current?.focus(); }} aria-label="Close navigation" /> : null}
      <aside id="primary-navigation" className={`sidebar upcode-sprint-sidebar ${open ? "open" : ""}`} aria-label="Application navigation">
        <div className="sidebar-brand">
          <div className={branding?.logo_url ? "organization-brand-mark" : "brand-mark"}>
            {branding?.logo_url ? <Image src={branding.logo_url} alt={`${branding.name} logo`} width={40} height={40} unoptimized /> : <Anchor aria-hidden />}
          </div>
          <div className="sidebar-brand-copy">
            <strong>Upcode sprint</strong>
            <span title={`${branding?.name ?? "Organization"} · Version ${branding?.version ?? "0.1.0"}`}>
              {branding?.name ?? "Organization"} · <code className="mono">v{branding?.version ?? "0.1.0"}</code>
            </span>
          </div>
          <Button ref={closeButtonRef} className="mobile-menu" style={{ marginLeft: "auto" }} variant="ghost" size="icon" onClick={() => { setOpen(false); menuButtonRef.current?.focus(); }} aria-label="Close navigation">
            <X />
          </Button>
        </div>

        <nav className="sidebar-nav" aria-label="Primary navigation">
          <div className="nav-category">Workspace</div>
          {workspace.filter((item) => !item.permission || hasPermission(item.permission)).map((item) => (
            <NavigationItem key={item.href} item={item} close={() => setOpen(false)} />
          ))}
          {visibleAdmin.length ? (
            <>
              <div className="nav-category">Administration</div>
              {visibleAdmin.map((item) => <NavigationItem key={item.href} item={item} close={() => setOpen(false)} />)}
            </>
          ) : null}
          <div className="nav-category">Account</div>
          <NavigationItem item={{ label: "Profile", href: "/profile", icon: UserRound }} close={() => setOpen(false)} />
        </nav>

        <div className="sidebar-footer">
          <div className="theme-selector" role="group" aria-label="Color theme">
            {themeChoices.map((choice) => {
              const Icon = choice.icon;
              const active = mounted && theme === choice.value;
              return (
                <button
                  className={`theme-option ${active ? "active" : ""}`}
                  type="button"
                  aria-pressed={active}
                  disabled={!mounted}
                  onClick={() => setTheme(choice.value)}
                  key={choice.value}
                >
                  <Icon aria-hidden />
                  <span>{choice.label}</span>
                </button>
              );
            })}
          </div>
          <div className="split">
            <Link href="/profile" className="user-chip">
              <UserAvatar user={user} />
              <div><strong>{user.display_name}</strong><span>{user.presence.status_message || `@${user.username}`}</span></div>
            </Link>
            <Button variant="ghost" size="icon" onClick={logout} aria-label="Log out"><LogOut /></Button>
          </div>
        </div>
      </aside>

      <div className="app-content">
        <header className="topbar">
          <Button
            ref={menuButtonRef}
            className="mobile-menu"
            variant="ghost"
            size="icon"
            onClick={() => setOpen(true)}
            aria-label="Open navigation"
            aria-controls="primary-navigation"
            aria-expanded={open}
          >
            <Menu />
          </Button>
          <div className="topbar-title"><strong>{title}</strong><span>{branding?.name ?? "Upcode sprint"}</span></div>
        </header>
        <main className="main-content" id="main-content"><div className="page-container">{children}</div></main>
      </div>
    </div>
  );
}
