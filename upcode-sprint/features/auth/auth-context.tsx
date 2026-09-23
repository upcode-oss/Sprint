"use client";

import { usePathname, useRouter } from "next/navigation";
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";

import { LoadingState } from "@/components/ui/states";
import { api } from "@/services/api";
import type { AuthUser } from "@/types/api";

type AuthContextValue = {
  user: AuthUser;
  hasPermission: (permission: string) => boolean;
  reload: () => Promise<void>;
};
const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const router = useRouter(); const pathname = usePathname();
  const [user, setUser] = useState<AuthUser>(); const [error, setError] = useState<string>();
  const reload = useCallback(async () => { const nextUser = await api<AuthUser>("/auth/me"); setUser(nextUser); }, []);
  useEffect(() => {
    reload().catch((reason: { status?: number; code?: string; message: string }) => {
      if (reason.code === "setup_required") router.replace("/setup");
      else if (reason.status === 401) router.replace(`/login?next=${encodeURIComponent(pathname)}`);
      else setError(reason.message);
    });
  }, [pathname, reload, router]);
  const value = useMemo(() => user ? { user, hasPermission: (permission: string) => user.permissions.includes(permission), reload } : null, [user, reload]);
  if (error) return <main className="centered-page"><p className="field-error">{error}</p></main>;
  if (!value) return <main className="centered-page"><LoadingState label="Loading workspace…" /></main>;
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used inside AuthProvider");
  return context;
}

